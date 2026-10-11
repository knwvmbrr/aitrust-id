"""One pinned FP32 English NLI backend; no model download or remote code loading."""
from pathlib import Path
import hashlib,json,importlib.metadata,time
from .pairs import PairError,require
MODEL_REVISION='a150876415327c80daeff35ca6f68f5ed8cf5c24'
EXPECTED={'model.onnx':('7105da41f625c42eca24e9465ec99150d02a80e644659d7a1daa93a6357155d4',284200859),'tokenizer.json':('5124ef2ead1a10a717703bc436de7f353da76d6340e4587719b42b1693707964',8656624),'config.json':('8d9f07bf7ba54a6fc3b1962483056f94c39dcf188db4cf61843e1c88f94b2342',1053)}
VERSIONS={'anyio': '4.15.1', 'click': '8.5.0', 'filelock': '4.1.1', 'flatbuffers': '25.12.19', 'fsspec': '2026.9.0', 'h11': '0.16.0', 'hf-xet': '1.7.0', 'httpcore2': '2.13.1', 'httpx2': '2.13.1', 'huggingface_hub': '2.2.0', 'idna': '3.20', 'ml_dtypes': '0.6.0', 'numpy': '2.5.4', 'onnx': '1.23.2', 'onnxruntime': '1.31.0', 'packaging': '26.3', 'protobuf': '7.36.2', 'PyYAML': '6.0.3', 'tokenizers': '0.23.3', 'tqdm': '4.70.1', 'truststore': '0.10.4', 'typing_extensions': '4.16.0'}

def expected_identity():
    return {'model_repository':'cross-encoder/nli-deberta-v3-xsmall','revision':MODEL_REVISION,'artifacts':{n:d for n,(d,s) in EXPECTED.items()},'runtime_versions':dict(VERSIONS),'provider':'CPUExecutionProvider','declared_label_order':['contradiction','entailment','neutral'],'scores_calibrated':False,'upstream_benchmark_is_product_accuracy':False}

class Backend:
    def __init__(self,cache,read_regular):
        # Caller supplies the repository's bounded descriptor reader, not arbitrary loading code.
        blobs={}
        for name,(digest,size) in EXPECTED.items():
            raw=read_regular(Path(cache)/name,size)
            require(len(raw)==size and hashlib.sha256(raw).hexdigest()==digest);blobs[name]=raw
        require(all(importlib.metadata.version(n)==v for n,v in VERSIONS.items()))
        config=json.loads(blobs['config.json'])
        require(config['id2label']=={'0':'contradiction','1':'entailment','2':'neutral'} and config['max_position_embeddings']==512)
        import numpy as np
        import onnx
        import onnxruntime as ort
        from tokenizers import Tokenizer
        graph=onnx.load_model_from_string(blobs['model.onnx'])
        require(not graph.functions and all(x.domain in ('','ai.onnx') for x in graph.opset_import))
        def inspect_graph(g):
            require(all(x.data_location!=onnx.TensorProto.EXTERNAL and not x.external_data for x in g.initializer))
            require(not g.sparse_initializer)
            for node in g.node:
                require(node.domain in ('','ai.onnx'))
                for a in node.attribute:
                    if a.type==onnx.AttributeProto.GRAPH:inspect_graph(a.g)
                    if a.type==onnx.AttributeProto.GRAPHS:
                        for child in a.graphs:inspect_graph(child)
                    if a.type==onnx.AttributeProto.TENSOR:require(a.t.data_location!=onnx.TensorProto.EXTERNAL and not a.t.external_data)
                    if a.type==onnx.AttributeProto.TENSORS:
                        require(all(t.data_location!=onnx.TensorProto.EXTERNAL and not t.external_data for t in a.tensors))
        inspect_graph(graph.graph);onnx.checker.check_model(graph)
        self.tokenizer=Tokenizer.from_str(blobs['tokenizer.json'].decode('utf-8','strict'))
        self.tokenizer.no_truncation();self.tokenizer.no_padding()
        options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
        self.session=ort.InferenceSession(blobs['model.onnx'],sess_options=options,providers=['CPUExecutionProvider'])
        require(self.session.get_providers()==['CPUExecutionProvider'])
        inputs=self.session.get_inputs();self.inputs=[x.name for x in inputs]
        require(set(self.inputs) in ({'input_ids','attention_mask'},{'input_ids','attention_mask','token_type_ids'}) and all(x.type=='tensor(int64)' for x in inputs))
        outputs=self.session.get_outputs();require(len(outputs)==1 and outputs[0].type=='tensor(float)')
        self.np=np
        self.identity=expected_identity()
    def __call__(self,first,second):
        encoding=self.tokenizer.encode(first,second)
        require(1<=len(encoding.ids)<=512)
        arrays={'input_ids':self.np.array([encoding.ids],dtype=self.np.int64),'attention_mask':self.np.array([encoding.attention_mask],dtype=self.np.int64),'token_type_ids':self.np.array([encoding.type_ids],dtype=self.np.int64)}
        result=self.session.run(None,{n:arrays[n] for n in self.inputs})
        require(len(result)==1 and result[0].shape==(1,3) and self.np.isfinite(result[0]).all())
        return [float(x) for x in result[0][0]],len(encoding.ids)
