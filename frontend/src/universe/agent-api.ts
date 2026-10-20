import type { CareerGraphData } from './universe-types';

export interface Activity { sequence: number; agent: string; type: string; status: string; at: string; message: string; payload: {tool?: string; related_entity?: string} }
export interface Effects { focus_role: string; highlight_skills: string[]; open_evidence: string | null }
export interface AgentResult { sections: {kind: string; data: unknown}[]; effects: Effects; profile_revision: string; notice: string }
export interface Execution {id: string; status: string; error_code: string | null; tool_count: number; token_usage: number; events: Activity[]; result: AgentResult | null}

export async function agentRequest(path: string, body?: object): Promise<Execution> {
  const response = await fetch('/api/agent-executions'+path, { method: body ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store',
    headers: body ? {'Content-Type':'application/json', 'X-Noka-CSRF':'1'} : {}, body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(response.status === 429 ? 'Session exploration limit reached. Try again later.' : 'AI exploration is unavailable. Your Universe is still available.');
  return response.json() as Promise<Execution>;
}

/** Treat model-selected UI effects as untrusted, including after a profile refresh. */
export function validEffects(result: AgentResult, graph: CareerGraphData): Effects | null {
  const e = result.effects;
  if (!e || (!graph.profile_revision || Date.parse(result.profile_revision) !== Date.parse(graph.profile_revision)) || !Array.isArray(e.highlight_skills)) return null;
  if (Object.keys(e).some(key => !['focus_role','highlight_skills','open_evidence'].includes(key)) || e.highlight_skills.length > 12) return null;
  if (!graph.nodes.some(n => n.id === e.focus_role && n.type === 'role')) return null;
  if (e.highlight_skills.some(id => !graph.nodes.some(n => n.id === id && ['owned_skill','required_skill'].includes(n.type)))) return null;
  if (e.open_evidence !== null && !graph.sources.some(s => s.id === e.open_evidence)) return null;
  return e;
}
