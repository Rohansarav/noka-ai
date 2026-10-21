import { expect,it,vi } from 'vitest';
import { render,screen } from '@testing-library/react';
import WorkspaceBoundary from './WorkspaceBoundary';
it('provides recovery for an unavailable view without exposing a technical trace',()=>{
  const error=vi.spyOn(console,'error').mockImplementation(()=>{});
  function BrokenView():never{throw new Error('internal-chunk-detail');}
  try{
    render(<WorkspaceBoundary><BrokenView/></WorkspaceBoundary>);
    expect(screen.getByRole('alert')).toHaveTextContent('Your workspace needs a refresh.');
    expect(screen.getByRole('button',{name:'Reload workspace'})).toBeVisible();
    expect(screen.queryByText('internal-chunk-detail')).not.toBeInTheDocument();
  }finally{error.mockRestore();}
});
