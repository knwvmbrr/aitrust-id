import React from 'react';
import Report from './Report.jsx';
import Assist from './Assist.jsx';
import Townhall from './Townhall.jsx';
import Teamwork from './Teamwork.jsx';
import HowTagsWork from './HowTagsWork.jsx';
import Scope from './Scope.jsx';
import About from './About.jsx';
import Legal from './Legal.jsx';
export const workflows=[
 {name:'Report',slug:'report',brief:'Challenge a finding',group:'Community'},
 {name:'Assist',slug:'assist',brief:'Contribute your skills',group:'Community'},
 {name:'Townhall',slug:'townhall',brief:'Read public conversations',group:'Community'},
 {name:'Teamwork',slug:'teamwork',brief:'See owners & open needs',group:'Community'},
 {name:'How tags work',slug:'how-tags-work',brief:'Follow answer → evidence',group:'Understand'},
 {name:'Scope',slug:'scope',brief:'Explore every job & outcome',group:'Understand'},
 {name:'About',slug:'about',brief:'Our purpose & progress',group:'Understand'},
 {name:'Legal',slug:'legal',brief:'Your rights & data',group:'Understand'},
];
export function WorkflowPanel({kind,tag,role,chooseContribution}){switch(kind){case 'Report':return <Report tag={tag}/>;case 'Assist':return <Assist tag={tag} initialRole={role}/>;case 'Townhall':return <Townhall/>;case 'Teamwork':return <Teamwork chooseContribution={chooseContribution}/>;case 'How tags work':return <HowTagsWork/>;case 'Scope':return <Scope/>;case 'About':return <About/>;case 'Legal':return <Legal/>;default:throw Error('Unknown workflow');}}
