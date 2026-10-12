import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import feedback_analysis as analysis
from tools.blind_review_io import source,create,PacketError

class Parser(argparse.ArgumentParser):
 def error(self,message):self.exit(2,'Feedback analysis refused; use --help for arguments.\n')

def main(argv=None):
 p=Parser(description='Compare private invented metadata batches; no collection, accuracy or training.')
 p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True)
 p.add_argument('--minimum-records',type=int,default=20);p.add_argument('--percentage-points',type=float,default=10)
 p.add_argument('--details',type=Path)
 a=p.parse_args(argv)
 try:
  before=analysis.parse(source(a.before,ROOT,analysis.MAX_BYTES));after=analysis.parse(source(a.after,ROOT,analysis.MAX_BYTES))
  result=analysis.compare(before,after,a.minimum_records,a.percentage_points)
  if a.details:create(a.details,ROOT,{'feedback-analysis.json':(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()})
  print(json.dumps({'profile':analysis.RESULT,'synthetic_only':True,'state':result['state'],'before_records':result['before']['records'],'after_records':result['after']['records'],'inspection_prompts':sum(row['inspection_prompt'] for row in result['comparisons']),'details_saved':a.details is not None,'accuracy_measured':False,'anomaly_diagnosed':False,'people_counted':False,'training_labels_created':False,'network_used':False,'next_step':('Inspect private category details; these reports are not confirmed errors.' if result['state']=='descriptive_changes' else 'The category proportions did not change. Counts remain available in private details.' if result['state']=='no_category_rate_change' else 'There are too few records for the inspection rule you chose. Counts remain available in private details.')}));return 0
 except (ValueError,TypeError,KeyError,OSError,UnicodeError,RecursionError,PacketError):
  print(json.dumps({'state':'UNAVAILABLE','reason':'private_synthetic_feedback_contract_refused','next_step':'Check the published batch fields, private file permissions and selected inspection rule.'}),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
