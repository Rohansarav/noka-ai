import { profileRequest } from '../profile-api';
import type { CareerGraphData } from './universe-types';

export async function getCareerGraph(): Promise<CareerGraphData> {
  const data = await profileRequest<CareerGraphData>('/current/career-graph');
  if (!data || !['no_profile', 'insufficient_profile_information', 'ready'].includes(data.status) || !Array.isArray(data.nodes) || !Array.isArray(data.edges) || !Array.isArray(data.sources) || !Array.isArray(data.limitations)) throw new Error('Unexpected universe response. Please retry.');
  const ids = new Set(data.nodes.map(n => n.id));
  if (ids.size !== data.nodes.length || data.edges.some(e => !ids.has(e.source) || !ids.has(e.target))) throw new Error('Incomplete universe connections. Please retry.');
  return data;
}
