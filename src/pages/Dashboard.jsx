import { useState, useEffect, useRef } from "react";
import { useDemoEngine } from "@/hooks/useDemoEngine";
import { searchKnowledge } from "@/lib/search";
import { Header, DemoTimeline } from "@/components/nwis/Header";
import { SearchBar } from "@/components/nwis/SearchBar";
import { LiveMonitor } from "@/components/nwis/LiveMonitor";
import { RiskGauge } from "@/components/nwis/RiskGauge";
import { CriticalBanner } from "@/components/nwis/CriticalBanner";
import { CaseFilePanel } from "@/components/nwis/CaseFilePanel";
import { NearbyWells } from "@/components/nwis/NearbyWells";
import { AlertLog } from "@/components/nwis/AlertLog";

export default function Dashboard() {
  const eng = useDemoEngine();
  const [selectedWellId, setSelectedWellId] = useState(null);
  const [search, setSearch] = useState(null);
  const [acked, setAcked] = useState(false);
  const caseRef = useRef(null);
  const wellsRef = useRef(null);

  useEffect(() => setAcked(false), [eng.session]);

  const onSearch = (q) => {
    const r = searchKnowledge(q);
    setSearch(r);
    if (r) setSelectedWellId(r.wellIds.size ? [...r.wellIds][0] : null);
  };
  const clearSearch = () => setSearch(null);
  const locate = (id) => {
    setSelectedWellId(id);
    wellsRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <div className="nwis-root font-body text-nw-text" data-testid="nwis-dashboard">
      {eng.phase === "critical" && !acked && <div className="critical-vignette" data-testid="critical-vignette" />}
      <CriticalBanner
        show={eng.criticalHit && !acked}
        risk={eng.current.risk}
        depth={eng.current.depth}
        onAck={() => setAcked(true)}
        onViewCase={() => caseRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })}
      />
      <div className="nwis-content max-w-[1760px] mx-auto px-4 sm:px-6 pb-10">
        <Header
          current={eng.current}
          tick={eng.tick}
          running={eng.running}
          phase={eng.phase}
          onToggle={() => eng.setRunning((r) => !r)}
          onSkip={eng.skip}
          onReplay={eng.replay}
        />
        <DemoTimeline tick={eng.tick} phase={eng.phase} />
        <SearchBar result={search} onSearch={onSearch} onClear={clearSearch} />

        <main className="grid grid-cols-12 gap-4 sm:gap-5 mt-5">
          <div className="col-span-12 xl:col-span-8 flex flex-col gap-4 sm:gap-5 min-w-0">
            <LiveMonitor points={eng.points} tick={eng.tick} phase={eng.phase} current={eng.current} />
            <div className="grid grid-cols-12 gap-4 sm:gap-5">
              <div className="col-span-12 2xl:col-span-8 min-w-0" ref={wellsRef}>
                <NearbyWells
                  selectedId={selectedWellId}
                  onSelect={setSelectedWellId}
                  search={search}
                  onClearSearch={clearSearch}
                  criticalHit={eng.criticalHit}
                />
              </div>
              <div className="col-span-12 2xl:col-span-4 min-w-0">
                <AlertLog alerts={eng.alerts} />
              </div>
            </div>
          </div>
          <div className="col-span-12 xl:col-span-4 flex flex-col gap-4 sm:gap-5 min-w-0">
            <RiskGauge risk={eng.current.risk} phase={eng.phase} criticalHit={eng.criticalHit} />
            <div ref={caseRef} className="flex-1 flex">
              <CaseFilePanel criticalHit={eng.criticalHit} current={eng.current} onLocate={locate} />
            </div>
          </div>
        </main>

        <footer className="mt-8 flex flex-col lg:flex-row items-center lg:items-center justify-between gap-2 text-[13px] text-nw-dim border-t border-nw-line/60 pt-4" data-testid="dashboard-footer">
          <span className="text-center lg:text-left">eRTMAC · NWIS proof-of-concept · Smart India Hackathon</span>
          <span className="font-mono text-center lg:text-right">Synthetic telemetry · Upper Assam Shelf offset archive · not for operational use</span>
        </footer>
      </div>
    </div>
  );
}


