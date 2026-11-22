#!/usr/bin/env python3
"""Emit a fixed synthetic reference fixture, NOT text from an AI model."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import synthid_input as vendor


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--unmarked',action='store_true')
    args=p.parse_args()
    try:
        vendor.source_identity()
        sys.path.insert(0,str(vendor.SDK))
        import torch
        from synthid_text.logits_processing import SynthIDLogitsProcessor
        torch.set_num_threads(1);torch.manual_seed(431)
        processor=SynthIDLogitsProcessor(ngram_len=5,key=654,depth=30,context_history_size=1024,device=torch.device('cpu'))
        ids=torch.tensor([[17]],dtype=torch.long);generated=[]
        for _ in range(96):
            scores=torch.zeros((1,64));scores[0,63]=-float('inf')
            token=torch.multinomial(torch.softmax(processor(ids,scores),dim=1),1)
            generated.append(int(token.item()));ids=torch.cat((ids,token),dim=1)
        if args.unmarked:generated=torch.randint(0,63,(96,)).tolist()
        packet={'profile':vendor.PROFILE,'public_key':654,'vocabulary_size':64,
                'eos_token_id':63,'token_ids':generated,'prompt_removed':True}
        print(json.dumps(packet,separators=(',',':')))
        return 0
    except Exception:
        print('UNAVAILABLE: reference practice generation did not complete.',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
