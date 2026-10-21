import { Component, type ReactNode } from 'react';

/** Recover cleanly when a deployed lazy bundle or a view fails to load. */
export default class WorkspaceBoundary extends Component<{children:ReactNode},{failed:boolean}> {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){
    if(this.state.failed) return <main className="workspace-recovery" role="alert"><p className="eyebrow">LET’S FIND YOUR WAY</p><h1>Your workspace needs a refresh.</h1><p>A view could not be displayed. Reload to load the current application version. Your saved profile and learning progress remain in your private session.</p><button className="button" onClick={()=>window.location.reload()}>Reload workspace</button></main>;
    return this.props.children;
  }
}
