import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { Compass, Leaf, Sparkles, Target, UserRound } from 'lucide-react';
import type { CSSProperties } from 'react';
import type { CareerNode } from './universe-types';

export type UniverseFlowNode = Node<{ entity: CareerNode; dimmed: boolean; scenarioLabel?: string; worldPriority?: boolean }, 'career'>;

// Official SDG palette, used as a decorative accent with separately readable text.
const SDG_COLORS = ['#E5243B','#DDA63A','#4C9F38','#C5192D','#FF3A21','#26BDE2','#FCC30B','#A21942','#FD6925','#DD1367','#FD9D24','#BF8B2E','#3F7E44','#0A97D9','#56C02B','#00689D','#19486A'];
export function sdgColor(goal: number | null) { return goal && goal >= 1 && goal <= 17 ? SDG_COLORS[goal - 1] : 'var(--color-green)'; }

export default function CareerNodeCard({ data, selected }: NodeProps<UniverseFlowNode>) {
  const node = data.entity;
  const Icon = node.type === 'profile' ? UserRound : node.type === 'role' ? Compass : node.type.startsWith('sdg') ? Leaf : node.type === 'required_skill' ? Target : Sparkles;
  const kind = node.type === 'profile' ? 'YOUR STARTING POINT' : node.type === 'role' ? (node.is_target?'YOUR TARGET':'POSSIBLE DIRECTION') : node.type === 'owned_skill' ? 'MY SKILL' : node.type === 'required_skill' ? 'SKILL TO BUILD' : node.type === 'context_skill' ? 'IMPACT CONTEXT SKILL' : node.type === 'technology' ? 'TECHNOLOGY TO EXPLORE' : node.type === 'sdg_target' ? 'VERIFIED TARGET' : 'GLOBAL GOAL';
  return <div className={`universe-node universe-node-${node.type}${data.dimmed ? ' is-muted' : ''}${selected ? ' is-selected' : ''}${data.worldPriority?' is-world-priority':''}`} style={{ '--sdg-accent': sdgColor(node.goal_id) } as CSSProperties}>
    <Handle id="target-right" type="target" position={Position.Right} isConnectable={false}/>
    <Handle id="target-top" type="target" position={Position.Top} isConnectable={false}/>
    <span className="universe-node-kicker"><Icon size={14} aria-hidden="true"/>{kind}</span>
    <strong>{node.label}</strong>
    {data.scenarioLabel && <span className="universe-world-label">{data.scenarioLabel}</span>}
    {node.type === 'profile' && <span>{node.skill_count} confirmed skills · {node.country} preference</span>}
    {node.type === 'owned_skill' && <span className="skill-level">{node.level === 'strong' ? 'Strong' : 'Developing · '+node.level} · self-reported</span>}
    {node.type === 'required_skill' && <span>Not recorded · published occupational requirement</span>}{node.type==='context_skill'&&<span>Published skill context · not a priority gap</span>}{node.type==='technology'&&<span>Published software example · alternatives may exist</span>}
    {node.type === 'role' && <span className="universe-node-score">{node.readiness_status==='not_assessed'?'Not assessed':node.score}<small>{node.readiness_status==='not_assessed'?'Broad occupational skills': '/ 100 documented coverage'}</small></span>}
    {node.type==='role'&&node.assessment&&<span>{node.assessment.recorded_count}/{node.assessment.required_count} requirements recorded · {node.assessment.status==='complete'?'complete evidence':'partial evidence'}</span>}{node.type === 'sdg' && <span>{node.description}</span>}
    {node.type === 'sdg_target' && <span>Reviewed relevance link</span>}
    <Handle id="source-left" type="source" position={Position.Left} isConnectable={false}/>
    <Handle id="source-bottom" type="source" position={Position.Bottom} isConnectable={false}/>
  </div>;
}
