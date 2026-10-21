import {describe,it,expect} from 'vitest';
import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import ReadinessEvidence from './ReadinessEvidence';

describe('transparent skill coverage',()=>{
  it('explains a sparse profile without presenting unknown skills as weaknesses',()=>{
    render(<MemoryRouter><ReadinessEvidence assessment={{required_count:25,recorded_count:4,unrecorded_count:21,evidence_completeness:20,assessed_proficiency:70,status:'partial',method:'Documented coverage = 20 × 70 / 100 = 14.'}}/></MemoryRouter>);
    expect(screen.getByText('Partial profile evidence')).toBeVisible();
    expect(screen.getByText(/21 unassessed/)).toBeVisible();
    expect(screen.getByText('70%')).toBeVisible();
    expect(screen.getByText(/does not establish low ability/)).toBeVisible();
    expect(screen.getByRole('link',{name:/Review my skills/})).toHaveAttribute('href','/profile/intake');
  });
  it('does not create a proficiency score when no role requirements are recorded',()=>{
    render(<MemoryRouter><ReadinessEvidence assessment={{required_count:10,recorded_count:0,unrecorded_count:10,evidence_completeness:0,assessed_proficiency:null,status:'unassessed',method:'Unrecorded requirements are unknown.'}}/></MemoryRouter>);
    expect(screen.getByText('Not assessed')).toBeVisible();
    expect(screen.queryByText('0% proficiency')).not.toBeInTheDocument();
  });
});
