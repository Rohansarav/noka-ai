import type { CareerGraphData } from './universe-types';

export interface Activity { sequence: number; agent: string; type: string; status: string; at: string; message: string; payload: {tool?: string; related_entity?: string; stage?: string; http_status?: number; provider_code?: string; error_type?: string; reason?: string} }
export interface Effects { focus_role: string; highlight_skills: string[]; open_evidence: string | null }
export interface AgentResult { sections: {kind: string; data: unknown}[]; effects: Effects; profile_revision: string; notice: string }
export interface Execution {id: string; status: string; error_code: string | null; tool_count: number; token_usage: number; events: Activity[]; result: AgentResult | null}

export function executionFailure(code: string | null): string {
  const messages: Record<string,string> = {
    ai_unavailable:'OpenAI is not configured on the server.',
    provider_authentication_error:'OpenAI rejected the server API credentials.',
    provider_permission_error:'This API project does not have permission for this request.',
    provider_model_unavailable:'The configured OpenAI model is unavailable to this project.',
    provider_quota_exceeded:'OpenAI reports insufficient API quota. Check this project’s API billing and limits.',
    provider_rate_limited:'OpenAI rate-limited this request. Try again later.',
    provider_request_rejected:'OpenAI rejected the request format. This needs an application fix.',
    provider_connection_error:'The server could not reach OpenAI.',
    execution_validation_error:'Noka could not validate a tool reference or result.',
    tool_arguments_invalid:'Noka rejected invalid tool arguments.',
    result_validation_error:'Noka could not validate the model’s result.',
    timeout:'The exploration exceeded its time limit.',
    profile_changed:'Your profile changed during exploration. Start again with your saved profile.',
  };
  return messages[code ?? ''] ?? 'AI exploration is unavailable.';
}

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
