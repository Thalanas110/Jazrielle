import { type ReactNode, useCallback, useEffect, useReducer, useRef, useState } from 'react';
import * as THREE from 'three';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';
import { AssistantPanel } from '@/components/assistant-panel';
import { FloatingLauncher } from '@/components/floating-launcher';
import {
  ArrowUpRight,
  ChevronDown,
  Command,
  Cpu,
  ExternalLink,
  History,
  LoaderCircle,
  LockKeyhole,
  RefreshCw,
  Send,
  Sparkles,
  Terminal,
} from 'lucide-react';
import {
  getGetJarvisCapabilitiesQueryKey,
  useExecuteJarvisCommand,
  useGetJarvisCapabilities,
  useRunJarvisInference,
} from '@/lib/api';
import {
  Route,
  Switch,
  useLocation,
  Router as WouterRouter,
} from 'wouter';
import { initialLauncherState, launcherReducer } from '@/lib/launcher-state';
import { useLauncherWindow } from '@/lib/use-launcher-window';

const queryClient = new QueryClient();

function Home() {
  const [launcherState, dispatch] = useReducer(launcherReducer, initialLauncherState);
  const launcherRoot = useRef<HTMLDivElement>(null);
  const closeLauncher = useCallback(() => dispatch({ type: 'close' }), []);
  const openLauncher = useCallback(() => dispatch({ type: 'open' }), []);
  useLauncherWindow(launcherState.mode, launcherRoot, closeLauncher);
  const [command, setCommand] = useState('');
  const [inference, setInference] = useState('');
  const [history, setHistory] = useState<Array<{ command: string; message: string; handled: boolean }>>([]);
  const [showCapabilities, setShowCapabilities] = useState(false);
  const commandInput = useRef<HTMLInputElement>(null);
  const capabilityQuery = useGetJarvisCapabilities({
    query: { queryKey: getGetJarvisCapabilitiesQueryKey() },
  });
  const executeCommand = useExecuteJarvisCommand();
  const runInference = useRunJarvisInference();
  const caps = capabilityQuery.data;
  const isExpanded = launcherState.mode === 'expanded';
  const isThinking = executeCommand.isPending || runInference.isPending;

  useEffect(() => {
    if (isExpanded) commandInput.current?.focus();
  }, [isExpanded]);

  const submitCommand = (value = command) => {
    const next = value.trim();
    if (!next || executeCommand.isPending) return;
    setCommand(next);
    executeCommand.mutate(
      { data: { command: next } },
      {
        onSuccess: (result) => {
          setHistory((items) => [{ command: next, message: result.message, handled: result.handled }, ...items].slice(0, 5));
          if (window.jazrielleDesktop && (result.app || result.launchUrl)) {
            void window.jazrielleDesktop.openTarget({ app: result.app, url: result.launchUrl });
          } else if (result.launchUrl) {
            window.open(result.launchUrl, '_blank', 'noopener,noreferrer');
          }
          setCommand('');
        },
      },
    );
  };

  const submitInference = () => {
    const prompt = inference.trim();
    if (!prompt || runInference.isPending) return;
    runInference.mutate({ data: { prompt, system: 'You are Jazrielle, a concise local desktop assistant. Be practical and brief.' } });
    setInference('');
  };

  const quickCommands = caps?.capabilities.flatMap((capability) => capability.examples.slice(0, 1).map((example) => ({ example, label: capability.label }))).slice(0, 4) ?? [
    { example: 'open calendar', label: 'Open calendar' },
    { example: 'open downloads', label: 'Open downloads' },
    { example: 'what time is it', label: 'Time check' },
  ];

  return (
    <main className={`jazrielle-stage ${isExpanded ? 'is-expanded' : 'is-collapsed'}`} ref={launcherRoot}>
      {!isExpanded ? (
        <FloatingLauncher active={isExpanded} thinking={isThinking} onOpen={openLauncher}>
          <OrbCanvas active={isThinking} />
        </FloatingLauncher>
      ) : (
        <AssistantPanel onClose={closeLauncher}>
          <div className="jazrielle-shell" data-testid="jazrielle-shell">

        <section className="presence-section">
          <div className={`orb-field ${executeCommand.isPending || runInference.isPending ? 'is-thinking' : ''}`} data-testid="presence-orb">
            <OrbCanvas active={executeCommand.isPending || runInference.isPending} />
            <div className="orb-label"><span className="status-kicker">{executeCommand.isPending || runInference.isPending ? 'PROCESSING' : 'READY'}</span><span className="status-sub">{caps?.localMode === false ? 'checking network' : 'computer boundary active'}</span></div>
          </div>
          <div className="presence-copy">
            <p className="section-kicker">COMMAND SURFACE <span>01</span></p>
            <h2>What should I<br /><em>make happen?</em></h2>
            <p className="supporting-copy">Deterministic actions stay here. Your files and routine commands never need a trip through the cloud.</p>
          </div>
        </section>

        <section className="command-zone">
          <form className="command-form" onSubmit={(event) => { event.preventDefault(); submitCommand(); }}>
            <Command size={17} className="command-symbol" />
            <input ref={commandInput} value={command} onChange={(event) => setCommand(event.target.value)} placeholder="Type a command…" aria-label="Command input" data-testid="input-command" autoComplete="off" />
            <kbd>↵</kbd>
            <button type="submit" className="send-button" aria-label="Run command" data-testid="button-run-command" disabled={!command.trim() || executeCommand.isPending}>
              {executeCommand.isPending ? <LoaderCircle size={16} className="spin" /> : <ArrowUpRight size={17} />}
            </button>
          </form>
          <div className="quick-row" aria-label="Quick commands">
            <span className="quick-label">TRY</span>
            {quickCommands.map(({ example, label }) => (
              <button type="button" key={example} className="quick-chip" onClick={() => submitCommand(example)} data-testid={`button-quick-${example.replace(/\s+/g, '-').toLowerCase()}`}>
                <span>{label}</span><ArrowUpRight size={12} />
              </button>
            ))}
          </div>
        </section>

        {executeCommand.isError && <div className="notice error-notice" data-testid="status-command-error"><span>{executeCommand.error instanceof Error ? executeCommand.error.message : 'Command unavailable.'}</span><button type="button" onClick={() => submitCommand(command)}>Retry</button></div>}
        {executeCommand.data && history[0]?.message && <div className={`notice result-notice ${executeCommand.data.handled ? '' : 'unhandled'}`} data-testid="status-command-result"><Terminal size={14} /><span>{executeCommand.data.message}</span>{executeCommand.data.app && <b>{executeCommand.data.app}</b>}</div>}

        <div className="lower-grid">
          <section className="panel history-panel">
            <div className="panel-heading"><div><p className="section-kicker">RECENT <span>02</span></p><h3><History size={15} /> Command history</h3></div><span className="tiny-count">{history.length ? `${history.length} / 5` : 'quiet'}</span></div>
            {history.length === 0 ? <div className="empty-history"><div className="empty-icon"><Terminal size={16} /></div><p>No commands yet</p><span>Completed actions will settle here.</span></div> : <div className="history-list">{history.map((item, index) => <button type="button" className="history-item" key={`${item.command}-${index}`} onClick={() => setCommand(item.command)} data-testid={`button-history-${index}`}><span className={`history-dot ${item.handled ? 'good' : 'muted'}`} /><span className="history-content"><b>{item.command}</b><small>{item.message}</small></span><ArrowUpRight size={13} /></button>)}</div>}
          </section>

          <section className="panel inference-panel">
            <div className="panel-heading"><div><p className="section-kicker">SECONDARY <span>03</span></p><h3><Sparkles size={15} /> Local thought</h3></div><span className={`model-state ${caps?.llmConfigured ? 'configured' : ''}`} data-testid="status-llm">{caps?.llmConfigured ? 'READY' : 'NOT SET'}</span></div>
            <p className="inference-note">For open-ended help, ask the local model. It never executes a command by itself.</p>
            <form className="inference-form" onSubmit={(event) => { event.preventDefault(); submitInference(); }}>
              <input value={inference} onChange={(event) => setInference(event.target.value)} placeholder="Ask for a thought…" aria-label="Local inference prompt" data-testid="input-inference" />
              <button type="submit" aria-label="Ask local model" data-testid="button-run-inference" disabled={!inference.trim() || runInference.isPending || caps?.llmConfigured === false}>{runInference.isPending ? <LoaderCircle size={15} className="spin" /> : <Send size={14} />}</button>
            </form>
            {runInference.isError && <p className="inline-error" data-testid="status-inference-error">Local inference could not be reached.</p>}
            {runInference.data && <div className="inference-response" data-testid="status-inference-response"><span>{runInference.data.model ?? 'LOCAL MODEL'}</span><p>{runInference.data.response}</p></div>}
          </section>
        </div>

        <footer className="shell-footer">
          <button type="button" className="capability-toggle" onClick={() => setShowCapabilities((shown) => !shown)} data-testid="button-toggle-capabilities"><Cpu size={14} /> {caps?.capabilities.length ?? 0} deterministic capabilities <ChevronDown size={14} className={showCapabilities ? 'rotate' : ''} /></button>
          <span><LockKeyhole size={12} /> private by default</span>
        </footer>
        {showCapabilities && <div className="capability-drawer" data-testid="panel-capabilities">{capabilityQuery.isLoading ? <div className="skeleton-line" /> : capabilityQuery.isError ? <div className="drawer-error"><p>Capabilities are offline.</p><button type="button" onClick={() => capabilityQuery.refetch()} data-testid="button-retry-capabilities"><RefreshCw size={13} /> Retry</button></div> : caps?.capabilities.map((capability) => <div className="capability-row" key={capability.id}><span className="capability-index">{capability.id.slice(0, 2).toUpperCase()}</span><div><b>{capability.label}</b><p>{capability.description}</p></div><ExternalLink size={13} /></div>)}</div>}
          </div>
        </AssistantPanel>
      )}
    </main>
  );
}

function OrbCanvas({ active }: { active: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    } catch {
      const context = canvas.getContext('2d');
      if (!context) return;
      let frame = 0;
      let animation = 0;
      const drawFallback = () => {
        const t = frame * 0.018;
        const cx = 95, cy = 95;
        context.clearRect(0, 0, 190, 190);
        for (let ring = 0; ring < 3; ring += 1) {
          const radius = 37 + ring * 12 + Math.sin(t * (ring + 1) + ring) * (active ? 3 : 1.5);
          context.beginPath();
          context.arc(cx, cy, radius, 0, Math.PI * 2);
          context.strokeStyle = `hsla(${166 + ring * 18}, 72%, ${70 - ring * 8}%, ${0.32 - ring * 0.06})`;
          context.lineWidth = ring === 0 ? 1.4 : 0.8;
          context.stroke();
        }
        const gradient = context.createRadialGradient(cx - 8, cy - 10, 1, cx, cy, 33);
        gradient.addColorStop(0, active ? 'rgba(242, 255, 246, .98)' : 'rgba(218, 255, 237, .95)');
        gradient.addColorStop(.25, 'rgba(117, 231, 196, .88)');
        gradient.addColorStop(1, 'rgba(25, 130, 125, .06)');
        context.fillStyle = gradient;
        context.beginPath();
        context.arc(cx, cy, 29 + Math.sin(t) * (active ? 3 : 1), 0, Math.PI * 2);
        context.fill();
        for (let point = 0; point < 18; point += 1) {
          const angle = point * 2.4 + t * (active ? 1.5 : .45);
          const radius = 46 + (point % 3) * 9;
          context.fillStyle = `hsla(${158 + point * 5}, 70%, 72%, ${point % 2 ? .22 : .48})`;
          context.fillRect(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius, 1.5, 1.5);
        }
        frame += 1;
        animation = requestAnimationFrame(drawFallback);
      };
      drawFallback();
      return () => cancelAnimationFrame(animation);
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(190, 190, false);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
    camera.position.z = 4.2;
    const group = new THREE.Group();
    scene.add(group);
    const orb = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.72, 3),
      new THREE.MeshBasicMaterial({ color: 0x79e7c4, wireframe: true, transparent: true, opacity: 0.82 }),
    );
    group.add(orb);
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.47, 24, 24),
      new THREE.MeshBasicMaterial({ color: 0xd9fff0, transparent: true, opacity: 0.2 }),
    );
    group.add(core);
    const rings = [1.08, 1.3, 1.52].map((radius, index) => {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(radius, index === 0 ? 0.009 : 0.006, 8, 96),
        new THREE.MeshBasicMaterial({ color: index === 1 ? 0xf2a184 : 0x52cbbb, transparent: true, opacity: 0.36 - index * 0.07 }),
      );
      ring.rotation.x = index * 0.7;
      ring.rotation.y = index * 0.35;
      group.add(ring);
      return ring;
    });
    let animation = 0;
    const startedAt = performance.now();
    const draw = (now: number) => {
      const time = (now - startedAt) / 1000;
      group.rotation.y = time * (active ? 0.8 : 0.28);
      group.rotation.x = Math.sin(time * 0.45) * 0.12;
      orb.scale.setScalar(1 + Math.sin(time * (active ? 4 : 1.5)) * (active ? 0.1 : 0.035));
      core.scale.setScalar(1 + Math.sin(time * (active ? 3.5 : 1.2)) * 0.1);
      rings.forEach((ring, index) => {
        ring.rotation.z = time * (index % 2 ? -0.35 : 0.22);
      });
      renderer.render(scene, camera);
      animation = requestAnimationFrame(draw);
    };
    animation = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animation);
      orb.geometry.dispose();
      (orb.material as THREE.Material).dispose();
      core.geometry.dispose();
      (core.material as THREE.Material).dispose();
      rings.forEach((ring) => {
        ring.geometry.dispose();
        (ring.material as THREE.Material).dispose();
      });
      renderer.dispose();
    };
  }, [active]);
  return <canvas ref={canvasRef} className="orb-canvas" aria-label="Reactive assistant presence" />;
}

function Router() {
  return (
    // Keep a shared shell (sidebar, navbar) outside the boundary so it
    // survives a page crash.
    <RoutedErrorBoundary>
      <Switch>
        <Route path="/" component={Home} />
        <Route component={NotFound} />
      </Switch>
    </RoutedErrorBoundary>
  );
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
