import React, {useEffect, useState} from 'react';
import {loadScope} from './scope-data.js';

export function ScopeData({children}) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState({data:null, error:false});
  useEffect(() => {
    let active = true;
    setState({data:null, error:false});
    loadScope().then(data => {
      if (active) setState({data, error:false});
    }, () => {
      if (active) setState({data:null, error:true});
    });
    return () => { active = false; };
  }, [attempt]);
  if (state.error) return <div data-scope-load-error className="my-3 text-sm leading-6">
    <p role="alert">Full scope details couldn’t load. Your tag check is still available.</p>
    <div className="mt-2 flex flex-wrap gap-3">
      <button type="button" className="min-h-11 rounded-lg border border-line px-3 font-medium" onClick={()=>setAttempt(n=>n+1)}>Try loading again</button>
      <a className="inline-flex min-h-11 items-center underline underline-offset-4" href="/reference/public-scope.json">Open complete scope file</a>
    </div>
  </div>;
  if (!state.data) return <p role="status" className="my-3 text-sm text-muted">Loading full scope details…</p>;
  return children(state.data);
}
