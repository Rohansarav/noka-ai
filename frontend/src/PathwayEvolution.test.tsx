import { expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import PathwayEvolution from './PathwayEvolution';
import { running, type ResearchRun } from './pathway-research-api';

it('labels synthetic review and sends a decision for the exact check',()=>{
  const onAction=vi.fn();
  const run={id:'run',status:'ready',evolution:{id:'check',mode:'simulation',status:'pending_review',message:'Review this fictional change.',sources:[]}} as unknown as ResearchRun;
  render(<PathwayEvolution run={run} busy={false} onAction={onAction}/>);
  expect(screen.getByText(/SIMULATION · fictional data/)).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Check reviewed evidence'})).toBeDisabled();
  fireEvent.click(screen.getByRole('button',{name:'Accept in simulation'}));
  expect(onAction).toHaveBeenCalledWith('/run/updates/decision',{check_id:'check',action:'accept'});
});

it('polls and displays actual pending analysis without a percent',()=>{
  const run={id:'run',status:'ready',evolution:{id:'check',mode:'evidence',status:'analyzing',message:'Comparing saved evidence.',sources:[]}} as unknown as ResearchRun;
  expect(running(run)).toBe(true);
  render(<PathwayEvolution run={run} busy={false} onAction={vi.fn()}/>);
  expect(screen.getByRole('status')).toHaveTextContent('Comparing saved evidence.');
  expect(screen.getByRole('button',{name:'Try synthetic replay'})).toBeDisabled();
  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
});
