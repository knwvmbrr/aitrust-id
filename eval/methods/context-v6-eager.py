"""Bounded command-pattern extraction. Scores are heuristics, not probabilities."""
import hashlib
import re
import shlex
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.body_limit import RequestBodyLimitMiddleware

app = FastAPI(title='AITrust-ID Evaluator')
app.add_middleware(RequestBodyLimitMiddleware,max_body_size=1_250_000)
PRODUCTION_TAGS = frozenset({'PS'})
CALIBRATION_ID = 'uncalibrated-rules-v6'
MODELS = [{'name':'rules-only','sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'revision':'context-v6'}]
FROZEN_WORD = '\\U00000030-\\U00000039\\U00000041-\\U0000005a\\U0000005f\\U00000061-\\U0000007a\\U000000aa\\U000000b2-\\U000000b3\\U000000b5\\U000000b9-\\U000000ba\\U000000bc-\\U000000be\\U000000c0-\\U000000d6\\U000000d8-\\U000000f6\\U000000f8-\\U000002c1\\U000002c6-\\U000002d1\\U000002e0-\\U000002e4\\U000002ec\\U000002ee\\U00000370-\\U00000374\\U00000376-\\U00000377\\U0000037a-\\U0000037d\\U0000037f\\U00000386\\U00000388-\\U0000038a\\U0000038c\\U0000038e-\\U000003a1\\U000003a3-\\U000003f5\\U000003f7-\\U00000481\\U0000048a-\\U0000052f\\U00000531-\\U00000556\\U00000559\\U00000560-\\U00000588\\U000005d0-\\U000005ea\\U000005ef-\\U000005f2\\U00000620-\\U0000064a\\U00000660-\\U00000669\\U0000066e-\\U0000066f\\U00000671-\\U000006d3\\U000006d5\\U000006e5-\\U000006e6\\U000006ee-\\U000006fc\\U000006ff\\U00000710\\U00000712-\\U0000072f\\U0000074d-\\U000007a5\\U000007b1\\U000007c0-\\U000007ea\\U000007f4-\\U000007f5\\U000007fa\\U00000800-\\U00000815\\U0000081a\\U00000824\\U00000828\\U00000840-\\U00000858\\U00000860-\\U0000086a\\U00000870-\\U00000887\\U00000889-\\U0000088e\\U000008a0-\\U000008c9\\U00000904-\\U00000939\\U0000093d\\U00000950\\U00000958-\\U00000961\\U00000966-\\U0000096f\\U00000971-\\U00000980\\U00000985-\\U0000098c\\U0000098f-\\U00000990\\U00000993-\\U000009a8\\U000009aa-\\U000009b0\\U000009b2\\U000009b6-\\U000009b9\\U000009bd\\U000009ce\\U000009dc-\\U000009dd\\U000009df-\\U000009e1\\U000009e6-\\U000009f1\\U000009f4-\\U000009f9\\U000009fc\\U00000a05-\\U00000a0a\\U00000a0f-\\U00000a10\\U00000a13-\\U00000a28\\U00000a2a-\\U00000a30\\U00000a32-\\U00000a33\\U00000a35-\\U00000a36\\U00000a38-\\U00000a39\\U00000a59-\\U00000a5c\\U00000a5e\\U00000a66-\\U00000a6f\\U00000a72-\\U00000a74\\U00000a85-\\U00000a8d\\U00000a8f-\\U00000a91\\U00000a93-\\U00000aa8\\U00000aaa-\\U00000ab0\\U00000ab2-\\U00000ab3\\U00000ab5-\\U00000ab9\\U00000abd\\U00000ad0\\U00000ae0-\\U00000ae1\\U00000ae6-\\U00000aef\\U00000af9\\U00000b05-\\U00000b0c\\U00000b0f-\\U00000b10\\U00000b13-\\U00000b28\\U00000b2a-\\U00000b30\\U00000b32-\\U00000b33\\U00000b35-\\U00000b39\\U00000b3d\\U00000b5c-\\U00000b5d\\U00000b5f-\\U00000b61\\U00000b66-\\U00000b6f\\U00000b71-\\U00000b77\\U00000b83\\U00000b85-\\U00000b8a\\U00000b8e-\\U00000b90\\U00000b92-\\U00000b95\\U00000b99-\\U00000b9a\\U00000b9c\\U00000b9e-\\U00000b9f\\U00000ba3-\\U00000ba4\\U00000ba8-\\U00000baa\\U00000bae-\\U00000bb9\\U00000bd0\\U00000be6-\\U00000bf2\\U00000c05-\\U00000c0c\\U00000c0e-\\U00000c10\\U00000c12-\\U00000c28\\U00000c2a-\\U00000c39\\U00000c3d\\U00000c58-\\U00000c5a\\U00000c5d\\U00000c60-\\U00000c61\\U00000c66-\\U00000c6f\\U00000c78-\\U00000c7e\\U00000c80\\U00000c85-\\U00000c8c\\U00000c8e-\\U00000c90\\U00000c92-\\U00000ca8\\U00000caa-\\U00000cb3\\U00000cb5-\\U00000cb9\\U00000cbd\\U00000cdd-\\U00000cde\\U00000ce0-\\U00000ce1\\U00000ce6-\\U00000cef\\U00000cf1-\\U00000cf2\\U00000d04-\\U00000d0c\\U00000d0e-\\U00000d10\\U00000d12-\\U00000d3a\\U00000d3d\\U00000d4e\\U00000d54-\\U00000d56\\U00000d58-\\U00000d61\\U00000d66-\\U00000d78\\U00000d7a-\\U00000d7f\\U00000d85-\\U00000d96\\U00000d9a-\\U00000db1\\U00000db3-\\U00000dbb\\U00000dbd\\U00000dc0-\\U00000dc6\\U00000de6-\\U00000def\\U00000e01-\\U00000e30\\U00000e32-\\U00000e33\\U00000e40-\\U00000e46\\U00000e50-\\U00000e59\\U00000e81-\\U00000e82\\U00000e84\\U00000e86-\\U00000e8a\\U00000e8c-\\U00000ea3\\U00000ea5\\U00000ea7-\\U00000eb0\\U00000eb2-\\U00000eb3\\U00000ebd\\U00000ec0-\\U00000ec4\\U00000ec6\\U00000ed0-\\U00000ed9\\U00000edc-\\U00000edf\\U00000f00\\U00000f20-\\U00000f33\\U00000f40-\\U00000f47\\U00000f49-\\U00000f6c\\U00000f88-\\U00000f8c\\U00001000-\\U0000102a\\U0000103f-\\U00001049\\U00001050-\\U00001055\\U0000105a-\\U0000105d\\U00001061\\U00001065-\\U00001066\\U0000106e-\\U00001070\\U00001075-\\U00001081\\U0000108e\\U00001090-\\U00001099\\U000010a0-\\U000010c5\\U000010c7\\U000010cd\\U000010d0-\\U000010fa\\U000010fc-\\U00001248\\U0000124a-\\U0000124d\\U00001250-\\U00001256\\U00001258\\U0000125a-\\U0000125d\\U00001260-\\U00001288\\U0000128a-\\U0000128d\\U00001290-\\U000012b0\\U000012b2-\\U000012b5\\U000012b8-\\U000012be\\U000012c0\\U000012c2-\\U000012c5\\U000012c8-\\U000012d6\\U000012d8-\\U00001310\\U00001312-\\U00001315\\U00001318-\\U0000135a\\U00001369-\\U0000137c\\U00001380-\\U0000138f\\U000013a0-\\U000013f5\\U000013f8-\\U000013fd\\U00001401-\\U0000166c\\U0000166f-\\U0000167f\\U00001681-\\U0000169a\\U000016a0-\\U000016ea\\U000016ee-\\U000016f8\\U00001700-\\U00001711\\U0000171f-\\U00001731\\U00001740-\\U00001751\\U00001760-\\U0000176c\\U0000176e-\\U00001770\\U00001780-\\U000017b3\\U000017d7\\U000017dc\\U000017e0-\\U000017e9\\U000017f0-\\U000017f9\\U00001810-\\U00001819\\U00001820-\\U00001878\\U00001880-\\U00001884\\U00001887-\\U000018a8\\U000018aa\\U000018b0-\\U000018f5\\U00001900-\\U0000191e\\U00001946-\\U0000196d\\U00001970-\\U00001974\\U00001980-\\U000019ab\\U000019b0-\\U000019c9\\U000019d0-\\U000019da\\U00001a00-\\U00001a16\\U00001a20-\\U00001a54\\U00001a80-\\U00001a89\\U00001a90-\\U00001a99\\U00001aa7\\U00001b05-\\U00001b33\\U00001b45-\\U00001b4c\\U00001b50-\\U00001b59\\U00001b83-\\U00001ba0\\U00001bae-\\U00001be5\\U00001c00-\\U00001c23\\U00001c40-\\U00001c49\\U00001c4d-\\U00001c7d\\U00001c80-\\U00001c88\\U00001c90-\\U00001cba\\U00001cbd-\\U00001cbf\\U00001ce9-\\U00001cec\\U00001cee-\\U00001cf3\\U00001cf5-\\U00001cf6\\U00001cfa\\U00001d00-\\U00001dbf\\U00001e00-\\U00001f15\\U00001f18-\\U00001f1d\\U00001f20-\\U00001f45\\U00001f48-\\U00001f4d\\U00001f50-\\U00001f57\\U00001f59\\U00001f5b\\U00001f5d\\U00001f5f-\\U00001f7d\\U00001f80-\\U00001fb4\\U00001fb6-\\U00001fbc\\U00001fbe\\U00001fc2-\\U00001fc4\\U00001fc6-\\U00001fcc\\U00001fd0-\\U00001fd3\\U00001fd6-\\U00001fdb\\U00001fe0-\\U00001fec\\U00001ff2-\\U00001ff4\\U00001ff6-\\U00001ffc\\U00002070-\\U00002071\\U00002074-\\U00002079\\U0000207f-\\U00002089\\U00002090-\\U0000209c\\U00002102\\U00002107\\U0000210a-\\U00002113\\U00002115\\U00002119-\\U0000211d\\U00002124\\U00002126\\U00002128\\U0000212a-\\U0000212d\\U0000212f-\\U00002139\\U0000213c-\\U0000213f\\U00002145-\\U00002149\\U0000214e\\U00002150-\\U00002189\\U00002460-\\U0000249b\\U000024ea-\\U000024ff\\U00002776-\\U00002793\\U00002c00-\\U00002ce4\\U00002ceb-\\U00002cee\\U00002cf2-\\U00002cf3\\U00002cfd\\U00002d00-\\U00002d25\\U00002d27\\U00002d2d\\U00002d30-\\U00002d67\\U00002d6f\\U00002d80-\\U00002d96\\U00002da0-\\U00002da6\\U00002da8-\\U00002dae\\U00002db0-\\U00002db6\\U00002db8-\\U00002dbe\\U00002dc0-\\U00002dc6\\U00002dc8-\\U00002dce\\U00002dd0-\\U00002dd6\\U00002dd8-\\U00002dde\\U00002e2f\\U00003005-\\U00003007\\U00003021-\\U00003029\\U00003031-\\U00003035\\U00003038-\\U0000303c\\U00003041-\\U00003096\\U0000309d-\\U0000309f\\U000030a1-\\U000030fa\\U000030fc-\\U000030ff\\U00003105-\\U0000312f\\U00003131-\\U0000318e\\U00003192-\\U00003195\\U000031a0-\\U000031bf\\U000031f0-\\U000031ff\\U00003220-\\U00003229\\U00003248-\\U0000324f\\U00003251-\\U0000325f\\U00003280-\\U00003289\\U000032b1-\\U000032bf\\U00003400-\\U00004dbf\\U00004e00-\\U0000a48c\\U0000a4d0-\\U0000a4fd\\U0000a500-\\U0000a60c\\U0000a610-\\U0000a62b\\U0000a640-\\U0000a66e\\U0000a67f-\\U0000a69d\\U0000a6a0-\\U0000a6ef\\U0000a717-\\U0000a71f\\U0000a722-\\U0000a788\\U0000a78b-\\U0000a7ca\\U0000a7d0-\\U0000a7d1\\U0000a7d3\\U0000a7d5-\\U0000a7d9\\U0000a7f2-\\U0000a801\\U0000a803-\\U0000a805\\U0000a807-\\U0000a80a\\U0000a80c-\\U0000a822\\U0000a830-\\U0000a835\\U0000a840-\\U0000a873\\U0000a882-\\U0000a8b3\\U0000a8d0-\\U0000a8d9\\U0000a8f2-\\U0000a8f7\\U0000a8fb\\U0000a8fd-\\U0000a8fe\\U0000a900-\\U0000a925\\U0000a930-\\U0000a946\\U0000a960-\\U0000a97c\\U0000a984-\\U0000a9b2\\U0000a9cf-\\U0000a9d9\\U0000a9e0-\\U0000a9e4\\U0000a9e6-\\U0000a9fe\\U0000aa00-\\U0000aa28\\U0000aa40-\\U0000aa42\\U0000aa44-\\U0000aa4b\\U0000aa50-\\U0000aa59\\U0000aa60-\\U0000aa76\\U0000aa7a\\U0000aa7e-\\U0000aaaf\\U0000aab1\\U0000aab5-\\U0000aab6\\U0000aab9-\\U0000aabd\\U0000aac0\\U0000aac2\\U0000aadb-\\U0000aadd\\U0000aae0-\\U0000aaea\\U0000aaf2-\\U0000aaf4\\U0000ab01-\\U0000ab06\\U0000ab09-\\U0000ab0e\\U0000ab11-\\U0000ab16\\U0000ab20-\\U0000ab26\\U0000ab28-\\U0000ab2e\\U0000ab30-\\U0000ab5a\\U0000ab5c-\\U0000ab69\\U0000ab70-\\U0000abe2\\U0000abf0-\\U0000abf9\\U0000ac00-\\U0000d7a3\\U0000d7b0-\\U0000d7c6\\U0000d7cb-\\U0000d7fb\\U0000f900-\\U0000fa6d\\U0000fa70-\\U0000fad9\\U0000fb00-\\U0000fb06\\U0000fb13-\\U0000fb17\\U0000fb1d\\U0000fb1f-\\U0000fb28\\U0000fb2a-\\U0000fb36\\U0000fb38-\\U0000fb3c\\U0000fb3e\\U0000fb40-\\U0000fb41\\U0000fb43-\\U0000fb44\\U0000fb46-\\U0000fbb1\\U0000fbd3-\\U0000fd3d\\U0000fd50-\\U0000fd8f\\U0000fd92-\\U0000fdc7\\U0000fdf0-\\U0000fdfb\\U0000fe70-\\U0000fe74\\U0000fe76-\\U0000fefc\\U0000ff10-\\U0000ff19\\U0000ff21-\\U0000ff3a\\U0000ff41-\\U0000ff5a\\U0000ff66-\\U0000ffbe\\U0000ffc2-\\U0000ffc7\\U0000ffca-\\U0000ffcf\\U0000ffd2-\\U0000ffd7\\U0000ffda-\\U0000ffdc\\U00010000-\\U0001000b\\U0001000d-\\U00010026\\U00010028-\\U0001003a\\U0001003c-\\U0001003d\\U0001003f-\\U0001004d\\U00010050-\\U0001005d\\U00010080-\\U000100fa\\U00010107-\\U00010133\\U00010140-\\U00010178\\U0001018a-\\U0001018b\\U00010280-\\U0001029c\\U000102a0-\\U000102d0\\U000102e1-\\U000102fb\\U00010300-\\U00010323\\U0001032d-\\U0001034a\\U00010350-\\U00010375\\U00010380-\\U0001039d\\U000103a0-\\U000103c3\\U000103c8-\\U000103cf\\U000103d1-\\U000103d5\\U00010400-\\U0001049d\\U000104a0-\\U000104a9\\U000104b0-\\U000104d3\\U000104d8-\\U000104fb\\U00010500-\\U00010527\\U00010530-\\U00010563\\U00010570-\\U0001057a\\U0001057c-\\U0001058a\\U0001058c-\\U00010592\\U00010594-\\U00010595\\U00010597-\\U000105a1\\U000105a3-\\U000105b1\\U000105b3-\\U000105b9\\U000105bb-\\U000105bc\\U00010600-\\U00010736\\U00010740-\\U00010755\\U00010760-\\U00010767\\U00010780-\\U00010785\\U00010787-\\U000107b0\\U000107b2-\\U000107ba\\U00010800-\\U00010805\\U00010808\\U0001080a-\\U00010835\\U00010837-\\U00010838\\U0001083c\\U0001083f-\\U00010855\\U00010858-\\U00010876\\U00010879-\\U0001089e\\U000108a7-\\U000108af\\U000108e0-\\U000108f2\\U000108f4-\\U000108f5\\U000108fb-\\U0001091b\\U00010920-\\U00010939\\U00010980-\\U000109b7\\U000109bc-\\U000109cf\\U000109d2-\\U00010a00\\U00010a10-\\U00010a13\\U00010a15-\\U00010a17\\U00010a19-\\U00010a35\\U00010a40-\\U00010a48\\U00010a60-\\U00010a7e\\U00010a80-\\U00010a9f\\U00010ac0-\\U00010ac7\\U00010ac9-\\U00010ae4\\U00010aeb-\\U00010aef\\U00010b00-\\U00010b35\\U00010b40-\\U00010b55\\U00010b58-\\U00010b72\\U00010b78-\\U00010b91\\U00010ba9-\\U00010baf\\U00010c00-\\U00010c48\\U00010c80-\\U00010cb2\\U00010cc0-\\U00010cf2\\U00010cfa-\\U00010d23\\U00010d30-\\U00010d39\\U00010e60-\\U00010e7e\\U00010e80-\\U00010ea9\\U00010eb0-\\U00010eb1\\U00010f00-\\U00010f27\\U00010f30-\\U00010f45\\U00010f51-\\U00010f54\\U00010f70-\\U00010f81\\U00010fb0-\\U00010fcb\\U00010fe0-\\U00010ff6\\U00011003-\\U00011037\\U00011052-\\U0001106f\\U00011071-\\U00011072\\U00011075\\U00011083-\\U000110af\\U000110d0-\\U000110e8\\U000110f0-\\U000110f9\\U00011103-\\U00011126\\U00011136-\\U0001113f\\U00011144\\U00011147\\U00011150-\\U00011172\\U00011176\\U00011183-\\U000111b2\\U000111c1-\\U000111c4\\U000111d0-\\U000111da\\U000111dc\\U000111e1-\\U000111f4\\U00011200-\\U00011211\\U00011213-\\U0001122b\\U0001123f-\\U00011240\\U00011280-\\U00011286\\U00011288\\U0001128a-\\U0001128d\\U0001128f-\\U0001129d\\U0001129f-\\U000112a8\\U000112b0-\\U000112de\\U000112f0-\\U000112f9\\U00011305-\\U0001130c\\U0001130f-\\U00011310\\U00011313-\\U00011328\\U0001132a-\\U00011330\\U00011332-\\U00011333\\U00011335-\\U00011339\\U0001133d\\U00011350\\U0001135d-\\U00011361\\U00011400-\\U00011434\\U00011447-\\U0001144a\\U00011450-\\U00011459\\U0001145f-\\U00011461\\U00011480-\\U000114af\\U000114c4-\\U000114c5\\U000114c7\\U000114d0-\\U000114d9\\U00011580-\\U000115ae\\U000115d8-\\U000115db\\U00011600-\\U0001162f\\U00011644\\U00011650-\\U00011659\\U00011680-\\U000116aa\\U000116b8\\U000116c0-\\U000116c9\\U00011700-\\U0001171a\\U00011730-\\U0001173b\\U00011740-\\U00011746\\U00011800-\\U0001182b\\U000118a0-\\U000118f2\\U000118ff-\\U00011906\\U00011909\\U0001190c-\\U00011913\\U00011915-\\U00011916\\U00011918-\\U0001192f\\U0001193f\\U00011941\\U00011950-\\U00011959\\U000119a0-\\U000119a7\\U000119aa-\\U000119d0\\U000119e1\\U000119e3\\U00011a00\\U00011a0b-\\U00011a32\\U00011a3a\\U00011a50\\U00011a5c-\\U00011a89\\U00011a9d\\U00011ab0-\\U00011af8\\U00011c00-\\U00011c08\\U00011c0a-\\U00011c2e\\U00011c40\\U00011c50-\\U00011c6c\\U00011c72-\\U00011c8f\\U00011d00-\\U00011d06\\U00011d08-\\U00011d09\\U00011d0b-\\U00011d30\\U00011d46\\U00011d50-\\U00011d59\\U00011d60-\\U00011d65\\U00011d67-\\U00011d68\\U00011d6a-\\U00011d89\\U00011d98\\U00011da0-\\U00011da9\\U00011ee0-\\U00011ef2\\U00011f02\\U00011f04-\\U00011f10\\U00011f12-\\U00011f33\\U00011f50-\\U00011f59\\U00011fb0\\U00011fc0-\\U00011fd4\\U00012000-\\U00012399\\U00012400-\\U0001246e\\U00012480-\\U00012543\\U00012f90-\\U00012ff0\\U00013000-\\U0001342f\\U00013441-\\U00013446\\U00014400-\\U00014646\\U00016800-\\U00016a38\\U00016a40-\\U00016a5e\\U00016a60-\\U00016a69\\U00016a70-\\U00016abe\\U00016ac0-\\U00016ac9\\U00016ad0-\\U00016aed\\U00016b00-\\U00016b2f\\U00016b40-\\U00016b43\\U00016b50-\\U00016b59\\U00016b5b-\\U00016b61\\U00016b63-\\U00016b77\\U00016b7d-\\U00016b8f\\U00016e40-\\U00016e96\\U00016f00-\\U00016f4a\\U00016f50\\U00016f93-\\U00016f9f\\U00016fe0-\\U00016fe1\\U00016fe3\\U00017000-\\U000187f7\\U00018800-\\U00018cd5\\U00018d00-\\U00018d08\\U0001aff0-\\U0001aff3\\U0001aff5-\\U0001affb\\U0001affd-\\U0001affe\\U0001b000-\\U0001b122\\U0001b132\\U0001b150-\\U0001b152\\U0001b155\\U0001b164-\\U0001b167\\U0001b170-\\U0001b2fb\\U0001bc00-\\U0001bc6a\\U0001bc70-\\U0001bc7c\\U0001bc80-\\U0001bc88\\U0001bc90-\\U0001bc99\\U0001d2c0-\\U0001d2d3\\U0001d2e0-\\U0001d2f3\\U0001d360-\\U0001d378\\U0001d400-\\U0001d454\\U0001d456-\\U0001d49c\\U0001d49e-\\U0001d49f\\U0001d4a2\\U0001d4a5-\\U0001d4a6\\U0001d4a9-\\U0001d4ac\\U0001d4ae-\\U0001d4b9\\U0001d4bb\\U0001d4bd-\\U0001d4c3\\U0001d4c5-\\U0001d505\\U0001d507-\\U0001d50a\\U0001d50d-\\U0001d514\\U0001d516-\\U0001d51c\\U0001d51e-\\U0001d539\\U0001d53b-\\U0001d53e\\U0001d540-\\U0001d544\\U0001d546\\U0001d54a-\\U0001d550\\U0001d552-\\U0001d6a5\\U0001d6a8-\\U0001d6c0\\U0001d6c2-\\U0001d6da\\U0001d6dc-\\U0001d6fa\\U0001d6fc-\\U0001d714\\U0001d716-\\U0001d734\\U0001d736-\\U0001d74e\\U0001d750-\\U0001d76e\\U0001d770-\\U0001d788\\U0001d78a-\\U0001d7a8\\U0001d7aa-\\U0001d7c2\\U0001d7c4-\\U0001d7cb\\U0001d7ce-\\U0001d7ff\\U0001df00-\\U0001df1e\\U0001df25-\\U0001df2a\\U0001e030-\\U0001e06d\\U0001e100-\\U0001e12c\\U0001e137-\\U0001e13d\\U0001e140-\\U0001e149\\U0001e14e\\U0001e290-\\U0001e2ad\\U0001e2c0-\\U0001e2eb\\U0001e2f0-\\U0001e2f9\\U0001e4d0-\\U0001e4eb\\U0001e4f0-\\U0001e4f9\\U0001e7e0-\\U0001e7e6\\U0001e7e8-\\U0001e7eb\\U0001e7ed-\\U0001e7ee\\U0001e7f0-\\U0001e7fe\\U0001e800-\\U0001e8c4\\U0001e8c7-\\U0001e8cf\\U0001e900-\\U0001e943\\U0001e94b\\U0001e950-\\U0001e959\\U0001ec71-\\U0001ecab\\U0001ecad-\\U0001ecaf\\U0001ecb1-\\U0001ecb4\\U0001ed01-\\U0001ed2d\\U0001ed2f-\\U0001ed3d\\U0001ee00-\\U0001ee03\\U0001ee05-\\U0001ee1f\\U0001ee21-\\U0001ee22\\U0001ee24\\U0001ee27\\U0001ee29-\\U0001ee32\\U0001ee34-\\U0001ee37\\U0001ee39\\U0001ee3b\\U0001ee42\\U0001ee47\\U0001ee49\\U0001ee4b\\U0001ee4d-\\U0001ee4f\\U0001ee51-\\U0001ee52\\U0001ee54\\U0001ee57\\U0001ee59\\U0001ee5b\\U0001ee5d\\U0001ee5f\\U0001ee61-\\U0001ee62\\U0001ee64\\U0001ee67-\\U0001ee6a\\U0001ee6c-\\U0001ee72\\U0001ee74-\\U0001ee77\\U0001ee79-\\U0001ee7c\\U0001ee7e\\U0001ee80-\\U0001ee89\\U0001ee8b-\\U0001ee9b\\U0001eea1-\\U0001eea3\\U0001eea5-\\U0001eea9\\U0001eeab-\\U0001eebb\\U0001f100-\\U0001f10c\\U0001fbf0-\\U0001fbf9\\U00020000-\\U0002a6df\\U0002a700-\\U0002b739\\U0002b740-\\U0002b81d\\U0002b820-\\U0002cea1\\U0002ceb0-\\U0002ebe0\\U0002f800-\\U0002fa1d\\U00030000-\\U0003134a\\U00031350-\\U000323af'

def compile_pattern(pattern, flags=0):
    word = '[' + FROZEN_WORD + ']'
    boundary = '(?:(?<!' + word + ')(?=' + word + ')|(?<=' + word + ')(?!' + word + '))'
    return re.compile(pattern.replace(r'\w', FROZEN_WORD).replace(r'\b', boundary), flags)

PIPED_TARGET = compile_pattern(r'\|\s*(?:sudo\s+)?(?:bash|sh)\b')
PIPED_INSTALLER = compile_pattern(r'(?<![\w./-])(?P<fetch>(?:curl|wget)\s+[^\n|;&`]*?)\s*\|\s*(?:sudo\s+)?(?:bash|sh)\b')
# The broad fetch_execute.v1 prototype is withdrawn from runtime; see signals.md.
# Full bounded expressions, output routing, and evaluation layers matter.
# These development methods do not fetch URLs or execute commands.
EXECUTOR = r'(?:(?:/(?:usr/)?bin/)?(?:bash|sh|zsh|dash|ksh))'
INTERPRETER = r'(?:(?:/(?:usr/)?bin/)?(?:python(?:[23])?|node|ruby|perl))'
COMMAND = r'(?P<executor>(?:'+EXECUTOR+r'\s+-(?:c|lc|cl)|'+INTERPRETER+r'\s+-(?:c|e)|eval))'
FETCH = r'(?P<fetch>(?:curl|wget)\s+[^()\n;$&|`]+?)'
PREFIX = r'(?<![\w./-])(?:sudo\s+)?'
COMMAND_SUBSTITUTION = compile_pattern(
    PREFIX+COMMAND+r'\s+(?P<quote>["\x27]?)\$\(\s*'+FETCH+r'\)(?P=quote)')
PROCESS_SUBSTITUTION = compile_pattern(
    PREFIX+r'(?:'+EXECUTOR+'|'+INTERPRETER+r'|source|\.)\s+<\(\s*'+FETCH+r'\)')
BACKTICK_SUBSTITUTION = compile_pattern(
    PREFIX+COMMAND+r'\s+(?P<quote>["\x27]?)`\s*'+FETCH+r'`(?P=quote)')


def fetches_stdout(fetch):
    """Tokenize only; never run a shell, fetch a URL, or evaluate a payload."""
    if re.search(r'(?:^|\s)(?:1)?>', fetch):
        return False
    try:
        args = shlex.split(fetch)
    except ValueError:
        return False
    if not args:
        return False
    curl = args[0] == 'curl'
    if args[0] not in ('curl', 'wget'):
        return False  # Shell command names and option letters are case-sensitive.
    stdout = curl
    # Consume option arguments instead of interpreting their letters as options.
    # This is bounded routing recognition, not a general curl/wget or shell parser.
    long_values = ({'--output', '--header', '--user-agent', '--user', '--proxy-user',
                    '--proxy', '--request', '--data', '--data-raw', '--data-binary',
                    '--form', '--referer', '--cookie', '--cookie-jar', '--max-time',
                    '--connect-timeout', '--range', '--url', '--write-out', '--dump-header'}
                   if curl else {'--output-document', '--header', '--user-agent',
                                 '--user', '--password', '--timeout', '--tries',
                                 '--directory-prefix', '--output-file'})
    short_values = 'AbcCdDeEFHmoruUw xXzT'.replace(' ', '') if curl else 'OUoPTt'
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == '--':
            break
        if arg.split('=', 1)[0] in ('--help', '--version') or (curl and arg.split('=', 1)[0] in ('--head', '--config', '--next')):
            return False
        if curl and arg in ('--remote-name', '--remote-name-all'):
            return False
        if arg.startswith('--'):
            key, equal, value = arg.partition('=')
            if key in long_values:
                if not equal:
                    i += 1
                    if i >= len(args):
                        return False
                    value = args[i]
                if key == ('--output' if curl else '--output-document'):
                    stdout = value == '-'
                    if not stdout:
                        return False
        elif arg.startswith('-') and arg != '-':
            flags = arg[1:]
            for pos, flag in enumerate(flags):
                if curl and flag in 'OIK':
                    return False
                if flag in short_values:
                    value = flags[pos + 1:]
                    if not value:
                        i += 1
                        if i >= len(args):
                            return False
                        value = args[i]
                    if flag == ('o' if curl else 'O'):
                        stdout = value == '-'
                        if not stdout:
                            return False
                    break
        i += 1
    return stdout


def display_quote(prefix):
    """Recognize an open literal echo/printf quote, never a later command."""
    command = compile_pattern(r'^\s*(?:echo|printf)\b').match(prefix)
    if not command:
        return None
    quote = None
    escaped = False
    for pos, char in enumerate(prefix[command.end():], command.end()):
        if escaped:
            escaped = False
            continue
        if char == '\\' and quote != "'":
            escaped = True
        elif char == quote:
            quote = None
        elif char in ('"', "'") and quote is None:
            quote = char
        elif quote is None and char in ';&|':
            return None
        elif quote != "'" and (char == '`' or prefix[pos:pos+2] == '$('):
            return None
    return quote


def build_context(text):
    """Index line and literal-display context once, rather than per finding."""
    size = len(text)
    lines = [0] * (size + 1)
    nonspace = [-1] * (size + 1)
    space = [-1] * (size + 1)
    quotes = [None] * (size + 1)
    metadata = {}
    line_start = previous_nonspace = previous_space = -1
    line_start = 0
    for pos, char in enumerate(text):
        lines[pos] = line_start
        nonspace[pos] = previous_nonspace
        space[pos] = previous_space
        if char.isspace():
            previous_space = pos
        else:
            previous_nonspace = pos
        if char == '\n':
            line_start = pos + 1
    lines[size] = line_start
    nonspace[size] = previous_nonspace
    space[size] = previous_space
    for line in re.finditer(r'[^\n]*', text):
        begin, end = line.span()
        # Ignore the zero-width match immediately before/after a real line.
        if begin in metadata:
            continue
        first = compile_pattern(r'\S').search(text, begin, end)
        comment_end = None
        if first and text[first.start()] == '#':
            comment_end = first.start() + 1
        elif first and text[first.start():first.start() + 2] == '//':
            comment_end = first.start() + 2
        command = compile_pattern(r'\s*(?:echo|printf)\b').match(text, begin, end)
        active = command is not None
        quote = None
        escaped = False
        metadata[begin] = {'comment_end': comment_end,
                           'dollar': text.find('$', begin, end),
                           'backtick': text.find('`', begin, end)}
        for pos in range(begin, end):
            quotes[pos] = quote if active else None
            if not active or pos < command.end():
                continue
            char = text[pos]
            if escaped:
                escaped = False
            elif char == '\\' and quote != "'":
                escaped = True
            elif char == quote:
                quote = None
            elif char in ('"', "'") and quote is None:
                quote = char
            elif quote is None and char in ';&|':
                active = False
            elif quote != "'" and (char == '`' or text[pos:pos+2] == '$('):
                active = False
        quotes[end] = quote if active else None
    return {'lines': lines, 'nonspace': nonspace, 'space': space,
            'quotes': quotes, 'metadata': metadata}


def warning_before(text, start, context):
    """Only the last three whitespace-separated words can form this grammar.

    Compress whitespace using indexed bounds; retain the suffix of a long
    first token because the original warning regex has no initial word boundary.
    """
    line = context['lines'][start]
    end = max(line, context['nonspace'][start] + 1)
    if end > line and text[end - 1] in ('`', '"', "'"):
        end = max(line, context['nonspace'][end - 1] + 1)
    words = []
    for _ in range(3):
        if end <= line:
            break
        begin = max(line, context['space'][end] + 1)
        words.insert(0, text[max(begin, end - 12):end])
        end = max(line, context['nonspace'][begin] + 1)
    return bool(WARNING.search(' '.join(words)))


def substitution_mentioned(text, match, context=None):
    context = context if context is not None else build_context(text)
    start = match.start()
    meta = context['metadata'][context['lines'][start]]
    if meta['comment_end'] is not None and start >= meta['comment_end']:
        return True
    return warning_before(text, start, context) or context['quotes'][start] == "'"


def pipe_mentioned(text, match, context=None):
    context = context if context is not None else build_context(text)
    if substitution_mentioned(text, match, context):
        return True
    meta = context['metadata'][context['lines'][match.start()]]
    literal = context['quotes'][match.start()] == '"'
    special = any(0 <= meta[key] < match.end() for key in ('dollar', 'backtick'))
    return literal and not special


def pipe_matches(text):
    """Scan disjoint delimiter windows, avoiding quadratic failed prefixes.

    Fetch text must be on the same physical line as its pipe. Whitespace after
    a pipe may continue onto the receiving shell, as in a shell pipeline.
    This remains token recognition, not a full shell parser.
    """
    begin = 0
    consumed = 0
    for delimiter in re.finditer(r'[|;&`\n]', text):
        pos = delimiter.start()
        if text[pos] == '|' and pos >= consumed:
            target = PIPED_TARGET.match(text, pos)
            if target:
                for match in PIPED_INSTALLER.finditer(text, begin, target.end()):
                    consumed = match.end()
                    yield match
        begin = delimiter.end()


def shell_evaluation_layer(match):
    quote = match.groupdict().get('quote')
    if quote != "'":
        return True
    executor = match.group('executor').split()[0].rsplit('/', 1)[-1].lower()
    return executor in ('bash', 'sh', 'zsh', 'dash', 'ksh', 'eval')

OBFUSCATED = compile_pattern(r'\b(?:eval|exec)\s*\(\s*(?:base64\.b64decode|atob|bytes\.fromhex)\s*\(', re.I)
# Narrow warning syntax scoped to the immediately preceding phrase. Not a broad
# character-window or fenced-code suppression rule.
WARNING = compile_pattern(r'(?:never\s+(?:run|execute|use)|do\s+not\s+(?:run|execute|use)|don\x27t\s+(?:run|execute|use)|avoid\s+(?:running|executing|using))\s*(?:[`"\x27]\s*)?$', re.I)

class Doc(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(max_length=200_000)

def mentioned(text, start, context=None):
    context = context if context is not None else build_context(text)
    meta = context['metadata'][context['lines'][start]]
    return ((meta['comment_end'] is not None and start >= meta['comment_end'])
            or warning_before(text, start, context))

@app.get('/healthz')
def healthz():
    return {'ok':True}

@app.post('/signals')
def signals(doc: Doc):
    signals = []
    context = build_context(doc.text)
    for pattern, name, score in [(PIPED_INSTALLER,'sig.piped_installer.v4',.97),(OBFUSCATED,'sig.obfuscated_payload.v3',.88)]:
        for match in (pipe_matches(doc.text) if pattern is PIPED_INSTALLER else pattern.finditer(doc.text)):
            if (not mentioned(doc.text,match.start(),context)
                    and (pattern is not PIPED_INSTALLER or
                         (not pipe_mentioned(doc.text, match,context) and fetches_stdout(match.group('fetch'))))):
                signals.append({'id':name,'score':score,'spans':[[match.start(),match.end()]]})
    for pattern, name in [(COMMAND_SUBSTITUTION, 'sig.remote_command_substitution.v4'),
                          (PROCESS_SUBSTITUTION, 'sig.remote_process_substitution.v4'),
                          (BACKTICK_SUBSTITUTION, 'sig.remote_backtick_substitution.v3')]:
        for match in pattern.finditer(doc.text):
            if (not substitution_mentioned(doc.text, match,context)
                    and (pattern is PROCESS_SUBSTITUTION or shell_evaluation_layer(match))
                    and fetches_stdout(match.group('fetch'))):
                signals.append({'id': name, 'score': .97,
                                'spans': [[match.start(), match.end()]]})
    candidates = [{'code':'PS','confidence':max(s['score'] for s in signals),'signals':signals}] if signals else []
    return {'candidates':candidates,'models':MODELS,'calibration_id':CALIBRATION_ID}
