import { type AnalyticsProvider, type AnalyticsRequest, type DashboardState } from "./contracts";
import { loadDashboard, snapshotState, unavailableSnapshot, validateRequest } from "./provider";

const loading: DashboardState = { status: "loading" };
type Options = {
  now?: () => number;
  schedule?: (callback: () => void, milliseconds: number) => () => void;
};

/** Owns request races and cache expiry independently of React rendering. */
export class DashboardController {
  private state: DashboardState = loading;
  private listeners = new Set<() => void>();
  private abort?: AbortController;
  private cancelExpiry?: () => void;
  private revision = 0;
  private request: AnalyticsRequest;
  private now: () => number;
  private schedule: NonNullable<Options["schedule"]>;

  constructor(private provider: AnalyticsProvider, request: AnalyticsRequest, options: Options = {}) {
    validateRequest(request);
    this.request = structuredClone(request);
    this.now = options.now ?? Date.now;
    this.schedule = options.schedule ?? ((callback, milliseconds) => {
      const timer = setTimeout(callback, milliseconds);
      return () => clearTimeout(timer);
    });
  }

  getSnapshot = () => this.state;
  getServerSnapshot = () => loading;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  };

  private publish(state: DashboardState) {
    this.state = state;
    this.listeners.forEach(listener => listener());
  }

  /** Safe on unmount, selection changes and React's development effect replay. */
  stop = () => {
    this.revision++;
    this.abort?.abort();
    this.cancelExpiry?.();
    this.cancelExpiry = undefined;
  };

  refresh = async () => {
    this.stop();
    const revision = this.revision;
    const abort = new AbortController();
    this.abort = abort;
    this.publish(loading);
    let result: DashboardState;
    try {
      result = await loadDashboard(this.provider, this.request, { signal: abort.signal, now: this.now });
    } catch {
      if (abort.signal.aborted || revision !== this.revision) return;
      result = snapshotState(unavailableSnapshot(this.request, this.provider.mode, this.now()), this.now());
    }
    if (abort.signal.aborted || revision !== this.revision) return;
    this.publish(result);
    if (result.status !== "stale" && result.status !== "unavailable") {
      const snapshot = result.snapshot;
      const expire = () => {
        if (abort.signal.aborted || revision !== this.revision) return;
        const remaining = Date.parse(snapshot.validUntil) - this.now() + 1;
        if (remaining > 0) {
          this.cancelExpiry = this.schedule(expire, Math.min(remaining, 2147483647));
        } else {
          this.publish(snapshotState(snapshot, this.now()));
        }
      };
      expire();
    }
  };
}
