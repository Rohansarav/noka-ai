import type { Source } from '../evidence-api';
import type { Level } from '../profile-api';

export type CareerNodeType = 'profile' | 'owned_skill' | 'required_skill' | 'role' | 'sdg' | 'sdg_target';
export type CareerEdgeType = 'has_skill' | 'requires_skill' | 'missing_skill' | 'contributes_to_target' | 'target_belongs_to_goal';
export type CareerNode = {
  id: string; type: CareerNodeType; entity_id: string; label: string; description: string;
  source_ids: string[]; review_status: string | null; level: Level | null; years: number | null;
  skill_count: number | null; country: string | null; is_demo: boolean; score: number | null;
  coverage: number | null; explanation: string | null; goal_id: number | null;
};
export type CareerEdge = {
  id: string; type: CareerEdgeType; source: string; target: string; source_ids: string[];
  importance: number | null; gap: number | null; critical: boolean; review_status: string | null;
  rationale: string | null; supporting_id: string | null;
};
export type CareerGraphData = {
  status: 'no_profile' | 'insufficient_profile_information' | 'ready'; profile_revision: string | null;
  generated_at: string; nodes: CareerNode[]; edges: CareerEdge[]; sources: Source[];
  methodology: string; limitations: string[];
};
export type UniverseFilter = 'all' | 'owned' | 'gaps' | 'sdgs';
