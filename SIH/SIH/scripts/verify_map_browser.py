"""Map regression checks against a running app and isolated Firefox BiDi session.

Start Firefox with --headless --no-remote --profile <temporary directory>
--remote-debugging-port 9223, then run:
  .venv/bin/python scripts/verify_map_browser.py

Uses websockets supplied by uvicorn[standard]; no frontend test dependency.
Only reads the live APIs. Replay controls and stored well data are untouched.
Screenshots go to the supplied --output directory (default: /tmp/nwis-map-review).
"""

import argparse
import asyncio
import base64
import json
from pathlib import Path

import websockets


MAP_HELPERS = r"""
(() => {
  const element = document.querySelector('.map-canvas');
  if (!element) return false;
  let fiber = element[Object.keys(element).find(key => key.startsWith('__reactFiber'))];
  while (fiber) {
    let map;
    let markers;
    for (let hook = fiber.memoizedState; hook; hook = hook.next) {
      if (hook.memoizedState?.current?.getStyle) {
        map = hook.memoizedState.current;
      }
      if (Array.isArray(hook.memoizedState?.current)) markers = hook.memoizedState;
    }
    if (map && markers?.current.length) {
      window.mapTest = { map, markers };
      return true;
    }
    fiber = fiber.return;
  }
  return false;
})()
"""

MARKER_CHECK = r"""
(() => {
  const map = window.mapTest.map;
  const container = map.getContainer().getBoundingClientRect();
  const markers = window.mapTest.markers.current.map(marker => {
    const anchor = marker.getElement();
    const button = anchor.querySelector('.well-marker');
    const rect = button.getBoundingClientRect();
    const projected = map.project(marker.getLngLat());
    const visible = getComputedStyle(button).display !== 'none';
    return {
      name: button.title.split(' · ')[0], visible,
      active: button.classList.contains('active-well'),
      position: getComputedStyle(anchor).position,
      width: rect.width, height: rect.height,
      drift: visible ? Math.hypot(
        rect.x + rect.width / 2 - container.x - projected.x,
        rect.y + rect.height / 2 - container.y - projected.y,
      ) : 0,
    };
  });
  return { zoom: map.getZoom(), markers };
})()
"""


async def main(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    async with websockets.connect(args.browser, max_size=30_000_000) as socket:
        sequence = 0

        async def call(method, params):
            nonlocal sequence
            sequence += 1
            await socket.send(json.dumps({'id': sequence, 'method': method, 'params': params}))
            while True:
                response = json.loads(await socket.recv())
                if response.get('id') == sequence:
                    if response.get('type') == 'error':
                        raise RuntimeError(response)
                    return response['result']

        await call('session.new', {'capabilities': {}})
        context = (await call('browsingContext.getTree', {}))['contexts'][0]['context']

        async def evaluate(expression):
            result = await call('script.evaluate', {
                'expression': f'(async () => JSON.stringify(await ({expression})))()',
                'target': {'context': context}, 'awaitPromise': True,
            })
            if result.get('type') == 'exception':
                raise AssertionError(result)
            return json.loads(result['result']['value'])

        async def wait_for(expression):
            for _ in range(100):
                if await evaluate(expression):
                    return
                await asyncio.sleep(0.2)
            raise AssertionError(f'Timed out: {expression}')

        async def click(text):
            await evaluate(f"(() => {{ [...document.querySelectorAll('button')].find(b => b.textContent.trim() === {json.dumps(text)}).click(); return true }})()")
            await asyncio.sleep(0.8)
            await wait_for('!window.mapTest.map.isMoving()')

        async def screenshot(name):
            result = await call('browsingContext.captureScreenshot', {'context': context})
            (output / f'{name}.png').write_bytes(base64.b64decode(result['data']))

        async def verify_markers():
            result = await evaluate(MARKER_CHECK)
            assert result['markers'], result
            for marker in result['markers']:
                assert marker['position'] == 'absolute', marker
                assert marker['width'] <= 26 and marker['height'] <= 26, marker
                assert marker['drift'] < 2, marker
            return result

        try:
            await call('browsingContext.setViewport', {
                'context': context, 'viewport': {'width': 1440, 'height': 1000},
            })
            await call('browsingContext.navigate', {'context': context, 'url': args.url, 'wait': 'complete'})
            await wait_for(MAP_HELPERS)
            await wait_for("!!window.mapTest.map.getSource('context-wells') && !!window.mapTest.map.getSource('radius') && window.mapTest.markers.current.length === 7")
            await wait_for("window.mapTest.map.isSourceLoaded('context-wells') && !window.mapTest.map.isMoving()")
            count = await evaluate("window.mapTest.map.getSource('context-wells').getData().then(data => data.features.length)")
            assert count == 24, count
            local = await verify_markers()
            assert len([m for m in local['markers'] if m['visible']]) == 7, local
            await screenshot('active-area')
            print('PASS: six local offsets + active well; 24 context wells loaded', flush=True)

            for zoom in (11, 8, 5, 2, 0):
                await evaluate(f"(() => {{window.mapTest.map.jumpTo({{center:[71.3924,25.7552],zoom:{zoom}}});return true}})()")
                await asyncio.sleep(0.4)
                result = await verify_markers()
                active = next(m for m in result['markers'] if m['active'])
                assert active['visible'], result
                if zoom < 6.5:
                    assert active['width'] < 12, active
                    assert not any(m['visible'] for m in result['markers'] if not m['active']), result
                print(f'PASS: zoom {zoom}; active symbol {active["width"]:.1f}px; coordinate drift <2px', flush=True)
            await screenshot('world-zoom')

            await click('India Overview')
            await wait_for("window.mapTest.map.isSourceLoaded('context-wells')")
            await asyncio.sleep(1)
            estate = await evaluate("(() => {const features=window.mapTest.map.queryRenderedFeatures({layers:['context-clusters','context-unclustered']});const unique=new Map(features.map(f=>[f.properties.cluster_id ?? f.properties.id,f]));return {symbols:unique.size,wells:[...unique.values()].reduce((sum,f)=>sum+(f.properties.point_count??1),0)}})()")
            assert estate['wells'] == 24 and estate['symbols'] >= 5, estate
            assert await evaluate("window.mapTest.map.getLayoutProperty('radius-line','visibility')") == 'none'
            await verify_markers()
            await screenshot('india-overview')
            print(f'PASS: India Overview renders all 24 context wells as {estate["symbols"]} compact symbols/clusters', flush=True)

            await click('Active Area')
            for radius, count in ((2, 4), (10, 7), (5, 7)):
                await click(f'{radius} km')
                await wait_for(f'window.mapTest.markers.current.length === {count}')
                await verify_markers()
                print(f'PASS: {radius} km radius has {count - 1} local offsets', flush=True)
            await evaluate("(() => {document.querySelector('.well-marker.offset-well').click();return true})()")
            await wait_for("!!document.querySelector('.well-drawer') && !!document.querySelector('.selected-well') && !window.mapTest.map.isMoving()")
            await verify_markers()
            await evaluate("(() => {document.querySelector('[aria-label=\"Close well details\"]').click();return true})()")
            print('PASS: offset selection, fly-to, outline, and drawer', flush=True)

            await evaluate("(() => {window.mapTest.map.fire('error',{sourceId:'india-official-boundary',error:new Error('test: overlay unavailable')});return true})()")
            assert not await evaluate("!!document.querySelector('.map-fallback')")
            print('PASS: overlay failure does not replace the working basemap', flush=True)

            await evaluate("(() => {const sourceId=Object.keys(window.mapTest.map.getStyle().sources).find(id=>!['context-wells','radius','india-official-boundary'].includes(id));window.mapTest.map.fire('error',{sourceId,error:new Error('test: basemap unavailable')});return true})()")
            await wait_for("!!document.querySelector('.map-fallback') && !!window.mapTest.map.getSource('context-wells') && !!window.mapTest.map.getSource('radius')")
            await click('India Overview')
            await wait_for("window.mapTest.map.isSourceLoaded('context-wells')")
            await asyncio.sleep(1)
            assert await evaluate("window.mapTest.map.queryRenderedFeatures({layers:['context-clusters','context-unclustered']}).length > 0")
            assert await evaluate("window.mapTest.map.queryRenderedFeatures({layers:['context-cluster-count']}).length > 0")
            await verify_markers()
            await screenshot('fallback-india')
            print('PASS: basemap failure retains context clusters, numbers, local geometry, and active symbol', flush=True)
            print(f'Screenshots: {output}', flush=True)
        finally:
            await call('session.end', {})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', default='ws://127.0.0.1:9223/session')
    parser.add_argument('--url', default='http://localhost:5173/live')
    parser.add_argument('--output', default='/tmp/nwis-map-review')
    asyncio.run(main(parser.parse_args()))
