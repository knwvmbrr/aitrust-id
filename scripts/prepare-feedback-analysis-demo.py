#!/usr/bin/env python3
"""Create two private invented metadata batches; no participants or collection."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.feedback_analysis import PROFILE
from tools.research_admission import CHOICES,FIXED
from tools.blind_review_io import create,PacketError

class Parser(argparse.ArgumentParser):
 def error(self,message):self.exit(2,'Feedback practice creation refused; use --help for arguments.\n')

def main(argv=None):
 p=Parser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
 try:
  files={}
  for name,index in [('before',0),('after',-1)]:
   row=dict(FIXED,**{key:choices[index] for key,choices in CHOICES.items()})
   value={'profile':PROFILE,'synthetic':True,'records':[dict(row) for _ in range(20)]}
   files[name+'.json']=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
  files['README.txt']=b'Invented practice metadata only. Each file has 20 repeated records, not 20 people.\nThe changed choices are not verified errors, accuracy evidence or training labels.\n'
  create(a.output,ROOT,files)
  print(json.dumps({'state':'synthetic_practice_created','files':3,'records_per_batch':20,'people_counted':False}));return 0
 except (ValueError,OSError,PacketError):
  print('Practice creation refused. Choose a new folder in an existing private directory outside the checkout.',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
