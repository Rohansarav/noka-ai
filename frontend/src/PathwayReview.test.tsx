import { expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PathwayReview from './PathwayReview';
import type { Task } from './future-api';

const mutate=vi.fn();
vi.mock('./future-api',()=>({useFuture:()=>({saving:false,progress:{mutate,isPending:false,isError:false}})}));
const task={skill_id:'monitor',name:'Monitoring',status:'planned',note:'Recorded observations and recovery checks.',assessment_needed:true,acceptance_criteria:['Include normal and abnormal observations.']} as Task;

it('shows evidence directly and prevents completion with unsaved edits',()=>{
 mutate.mockClear();
 const view=render(<MemoryRouter><PathwayReview task={task}/></MemoryRouter>);
 expect(screen.getByRole('textbox',{name:'Monitoring notes'})).toBeVisible();
 expect(screen.getByRole('button',{name:'Mark step complete'})).toBeEnabled();
 fireEvent.change(screen.getByRole('textbox'),{target:{value:'Changed observations with more details.'}});
 expect(screen.getByText('Unsaved changes')).toBeVisible();
 expect(screen.getByRole('button',{name:'Mark step complete'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Save evidence'}));
 expect(mutate).toHaveBeenLastCalledWith({skill_id:'monitor',note:'Changed observations with more details.'});
 view.rerender(<MemoryRouter><PathwayReview task={{...task,note:'Changed observations with more details.'}}/></MemoryRouter>);
 expect(screen.getByText('Saved')).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Mark step complete'}));
 expect(mutate).toHaveBeenLastCalledWith({skill_id:'monitor',status:'completed'});
});

it('checklist ticks do not establish competence or bypass missing evidence',()=>{
 mutate.mockClear();
 render(<MemoryRouter><PathwayReview task={{...task,note:'',assessment_needed:false}}/></MemoryRouter>);
 fireEvent.click(screen.getByRole('checkbox'));
 expect(mutate).not.toHaveBeenCalled();
 expect(screen.getByRole('button',{name:'Mark step complete'})).toBeDisabled();
 expect(screen.queryByText('Already comfortable with this?')).not.toBeInTheDocument();
 expect(screen.getByText(/does not verify competence/)).toBeVisible();
});
