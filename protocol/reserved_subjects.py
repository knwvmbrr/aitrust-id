"""Bounded decoded-artifact subjects. No decoding, detection, persistence or adoption."""
import base64
import binascii
import hashlib
import struct
from protocol.normalization import normalize_nfc, NORMALIZATION_ID

VERSION='reserved-subject-v1'
MAX_BINARY=1_048_576
MAX_VIDEO_BYTES=4_194_304
MAX_REQUEST_BYTES=8_388_608

def fields(value, expected):
    if type(value) is not dict or set(value)!=set(expected):raise ValueError('Unexpected artifact fields')
def integer(value, minimum, maximum):
    if type(value) not in (int,float) or type(value) is float and not value.is_integer() or not minimum<=value<=maximum:raise ValueError('Invalid integer')
    return int(value)
def binary(value, maximum=MAX_BINARY):
    if type(value) is not str or len(value)>4*((maximum+2)//3):raise ValueError('Invalid binary size/type')
    try:raw=base64.b64decode(value,validate=True)
    except (ValueError,binascii.Error):raise ValueError('Invalid base64') from None
    if len(raw)>maximum or base64.b64encode(raw).decode()!=value:raise ValueError('Noncanonical or oversized base64')
    return raw
def packed(kind, parts):
    result=bytearray((VERSION+'\0'+kind+'\0').encode('ascii'))
    for part in parts:
        raw=part if type(part) is bytes else str(part).encode('utf-8')
        result.extend(struct.pack('>I',len(raw)));result.extend(raw)
    return bytes(result)
def digest(kind, parts):return hashlib.sha256(packed(kind,parts)).hexdigest()

def image(value):
    fields(value,['modality','width','height','representation','pixels_base64'])
    if value['modality']!='image' or value['representation']!='RGBA8-sRGB-straight-oriented':raise ValueError('Unsupported image representation')
    width=integer(value['width'],1,262_144);height=integer(value['height'],1,262_144)
    if width*height>262_144:raise ValueError('Oversized pixel count')
    raw=binary(value['pixels_base64'])
    if len(raw)!=width*height*4:raise ValueError('Pixel buffer mismatch')
    return {'modality':'image','contract_version':VERSION,'sha256':digest('image',[width,height,value['representation'],raw]),'width':width,'height':height,'offset_unit':'pixel_xy_half_open'},len(raw)

def audio(value):
    fields(value,['modality','sample_rate','channels','representation','samples_base64'])
    if value['modality']!='audio' or value['representation']!='PCM16LE-interleaved':raise ValueError('Unsupported audio representation')
    rate=integer(value['sample_rate'],8_000,192_000);channels=integer(value['channels'],1,8)
    raw=binary(value['samples_base64'])
    if not raw or len(raw)%(2*channels):raise ValueError('Incomplete audio frame')
    frames=len(raw)//(2*channels)
    return {'modality':'audio','contract_version':VERSION,'sha256':digest('audio',[rate,channels,value['representation'],raw]),'frames':frames,'sample_rate':rate,'channels':channels,'offset_unit':'sample_frame_half_open','time_base':{'numerator':1,'denominator':rate}}

def video(value):
    fields(value,['modality','representation','frames'])
    if value['modality']!='video' or value['representation']!='decoded-frames-us-v1':raise ValueError('Unsupported video representation')
    frames=value['frames']
    if type(frames) is not list or not 1<=len(frames)<=64:raise ValueError('Invalid frame count')
    leaves=[];total=0;previous_end=0;manifest=[]
    for index,frame in enumerate(frames):
        fields(frame,['timestamp_us','duration_us','image'])
        timestamp=integer(frame['timestamp_us'],0,2**53-1);duration=integer(frame['duration_us'],1,2**53-1)
        if timestamp+duration>2**53-1 or index and timestamp<previous_end:raise ValueError('Overlapping/unsafe video timing')
        subject,size=image(frame['image']);total+=size
        if total>MAX_VIDEO_BYTES:raise ValueError('Oversized video buffers')
        previous_end=timestamp+duration
        leaves.append(digest('video-leaf',[index,timestamp,duration,bytes.fromhex(subject['sha256'])]))
        manifest.append({'index':index,'timestamp_us':timestamp,'duration_us':duration,'image':subject})
    nodes=leaves[:]
    while len(nodes)>1:
        nodes=[digest('video-pair',[bytes.fromhex(nodes[i]),bytes.fromhex(nodes[i+1])]) if i+1<len(nodes) else nodes[i] for i in range(0,len(nodes),2)]
    return {'modality':'video','contract_version':VERSION,'sha256':digest('video',[len(frames),value['representation'],bytes.fromhex(nodes[0])]),'frames':manifest,'merkle_rule':'ordered-domain-separated-pairs; odd node promoted','offset_unit':'frame_index_pixel_xy_half_open','time_unit':'microsecond'}

def document(value):
    fields(value,['modality','extraction_profile','pages'])
    if value['modality']!='document' or value['extraction_profile']!='supplied-page-text-v1':raise ValueError('Unsupported extraction profile')
    pages=value['pages']
    if type(pages) is not list or not 1<=len(pages)<=100:raise ValueError('Invalid page count')
    page_hashes=[];manifest=[];characters=0;asset_count=0;asset_bytes=0
    for index,page in enumerate(pages):
        fields(page,['text','assets'])
        text=page['text'];assets=page['assets']
        if type(text) is not str:raise ValueError('Invalid page text')
        characters+=len(text)
        if characters>200_000:raise ValueError('Oversized document text')
        normalized=normalize_nfc(text)
        if type(assets) is not list:raise ValueError('Invalid assets')
        asset_count+=len(assets)
        if asset_count>64:raise ValueError('Too many document assets')
        parts=[index,NORMALIZATION_ID,normalized.encode('utf-8'),len(assets)];asset_manifest=[]
        for asset_index,asset in enumerate(assets):
            fields(asset,['media_type','data_base64'])
            media=asset['media_type']
            if type(media) is not str or not 1<=len(media)<=64 or len(media.split('/'))!=2 or not all(media.split('/')) or any(not (c.isascii() and (c.isalnum() or c in '/.+-')) for c in media):raise ValueError('Invalid asset media type')
            raw=binary(asset['data_base64']);asset_bytes+=len(raw)
            if asset_bytes>MAX_BINARY:raise ValueError('Oversized document assets')
            subject=digest('document-asset',[asset_index,media,raw]);parts.append(bytes.fromhex(subject));asset_manifest.append({'index':asset_index,'media_type':media,'bytes':len(raw),'sha256':subject})
        page_hash=digest('document-page',parts);page_hashes.append(bytes.fromhex(page_hash));manifest.append({'index':index,'characters':len(normalized),'sha256':page_hash,'assets':asset_manifest})
    return {'modality':'document','contract_version':VERSION,'sha256':digest('document',[value['extraction_profile'],NORMALIZATION_ID,len(pages),*page_hashes]),'extraction_profile':value['extraction_profile'],'normalization_id':NORMALIZATION_ID,'pages':manifest,'offset_unit':'page_index_unicode_codepoint_half_open'}

def subject(value):
    if type(value) is not dict:raise ValueError('Invalid artifact')
    modality=value.get('modality')
    if modality=='image':return image(value)[0]
    if modality=='audio':return audio(value)
    if modality=='video':return video(value)
    if modality=='document':return document(value)
    raise ValueError('Unsupported reserved subject modality')

def validate_span(artifact, span):
    """Validate coordinates against a freshly computed subject, never a claimed size."""
    result=subject(artifact);modality=result['modality']
    def interval(value, maximum):
        if type(value) is not list or len(value)!=2:raise ValueError('Invalid interval')
        start=integer(value[0],0,maximum);end=integer(value[1],0,maximum)
        if start>=end:raise ValueError('Empty/reversed interval')
        return [start,end]
    def box(value, width, height):
        if type(value) is not list or len(value)!=4:raise ValueError('Invalid box')
        x0,x1=interval([value[0],value[2]],width);y0,y1=interval([value[1],value[3]],height)
        return [x0,y0,x1,y1]
    if modality=='image':return box(span,result['width'],result['height'])
    if modality=='audio':return interval(span,result['frames'])
    if modality=='video':
        fields(span,['frame','box']);index=integer(span['frame'],0,len(result['frames'])-1);image=result['frames'][index]['image']
        return {'frame':index,'box':box(span['box'],image['width'],image['height'])}
    fields(span,['page','range']);index=integer(span['page'],0,len(result['pages'])-1)
    return {'page':index,'range':interval(span['range'],result['pages'][index]['characters'])}
