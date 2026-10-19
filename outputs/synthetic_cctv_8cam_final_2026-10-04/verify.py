"""Inspect the encoded footage and optionally test the existing YOLO detector."""

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np


def probe(path):
    result=subprocess.run(['ffprobe','-v','error','-select_streams','v:0',
        '-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames',
        '-show_entries','format=duration','-show_frames',
        '-show_entries','frame=best_effort_timestamp_time',
        '-of','json',str(path)],capture_output=True,text=True,check=True)
    raw=json.loads(result.stdout)
    timestamps=[float(f['best_effort_timestamp_time']) for f in raw['frames']]
    decode=subprocess.run(['ffmpeg','-v','error','-threads','1','-i',str(path),
        '-f','null','-'],capture_output=True,text=True)
    return dict(file=path.name,bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                stream=raw['streams'][0],duration=float(raw['format']['duration']),
                timestamps=timestamps,full_decode_pass=decode.returncode==0 and not decode.stderr.strip(),
                decoder_errors=decode.stderr[:2000])


def snapshot(path,time):
    cap=cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_MSEC,time*1000)
    success,frame=cap.read();cap.release()
    if not success:raise RuntimeError(f'Cannot read {path} at {time}')
    return frame


def overlap(a,b):
    iw=max(0,min(a[2],b[2])-max(a[0],b[0]));ih=max(0,min(a[3],b[3])-max(a[1],b[1]))
    inter=iw*ih
    return inter/max((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter,1)


def detector_check(root,model_path,observations):
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(2)
    model=YOLO(str(model_path));records=[]
    for cam in range(1,9):
        path=root/f'cam{cam:02d}.mp4';frame=snapshot(path,22)
        gt=observations[(f'cam{cam:02d}',220)]
        result=model.predict(frame,classes=[0],conf=.25,imgsz=960,device='cpu',verbose=False)[0]
        detections=[];used=set();matched=0;role_correct=0
        for raw in result.boxes.xyxy.cpu().numpy():
            x0,y0,x1,y1=np.round(raw).astype(int)
            x0=max(0,x0);y0=max(0,y0);x1=min(frame.shape[1],x1);y1=min(frame.shape[0],y1)
            # Color is a fixture-level flag, not authoritative real-world role inference.
            crop=frame[y0+int((y1-y0)*.12):y0+int((y1-y0)*.65),x0:x1]
            fraction=0.0
            if crop.size:
                hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
                mask=cv2.inRange(hsv,np.array([2,145,105]),np.array([25,255,255]))
                fraction=float(np.count_nonzero(mask)/mask.size)
            role='employee' if fraction>.07 else 'customer'
            candidate=[(overlap(raw,g['bbox_xyxy']),i,g) for i,g in enumerate(gt) if i not in used]
            best=max(candidate,default=(0,None,None),key=lambda a:a[0])
            reference=None
            if best[0]>=.35:
                used.add(best[1]);matched+=1;reference=best[2]
                role_correct+=int(role==reference['role'])
            detections.append(dict(box=[int(x0),int(y0),int(x1),int(y1)],
                fixture_color_role=role,orange_fraction=round(fraction,4),
                matched_person_id=reference['person_id'] if reference else None,
                matched_ground_truth_role=reference['role'] if reference else None))
            color=(0,145,255) if role=='employee' else (235,160,45)
            cv2.rectangle(frame,(x0,y0),(x1,y1),color,2)
            cv2.putText(frame,role,(x0,max(50,y0-5)),cv2.FONT_HERSHEY_SIMPLEX,.42,color,1,cv2.LINE_AA)
        cv2.imwrite(str(root/f'yolo_check_cam{cam:02d}.jpg'),frame)
        records.append(dict(camera_id=f'cam{cam:02d}',time_seconds=22,
            visible_ground_truth_people=len(gt),person_detections=len(detections),
            matched_people_iou_035=matched,matched_color_roles_correct=role_correct,
            detections=detections))
    totals=dict(ground_truth=sum(r['visible_ground_truth_people'] for r in records),
        detections=sum(r['person_detections'] for r in records),
        matched=sum(r['matched_people_iou_035'] for r in records),
        matched_color_roles_correct=sum(r['matched_color_roles_correct'] for r in records))
    return dict(model=model_path.name,confidence=.25,imgsz=960,
        note='Eight single-frame smoke checks at 22s. Not a held-out benchmark; color rule is only for synthetic fixtures.',
        totals=totals,cameras=records)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).parent)
    p.add_argument('--model',type=Path);args=p.parse_args();root=args.root.resolve()
    manifest=json.loads((root/'manifest.json').read_text())
    paths=[root/f'cam{i:02d}.mp4' for i in range(1,9)]+[root/'security_monitor_8cams.mp4']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(probe,paths))
    expected=manifest['frame_count'];fps=manifest['fps'];reference=np.arange(expected)/fps
    for r in results:
        ts=np.array(r.pop('timestamps'))
        assert len(ts)==expected,(r['file'],len(ts),expected)
        assert np.allclose(ts,reference,atol=.000001),(r['file'],'timestamp mismatch')
        assert r['full_decode_pass'],(r['file'],r['decoder_errors'])
        assert abs(r['duration']-manifest['duration_seconds'])<.001
        assert r['stream']['codec_name']=='h264'
        r['frame_timestamp_alignment_pass']=True
        r['timestamp_sequence_sha256']=hashlib.sha256(ts.tobytes()).hexdigest()
    actor_registry={a['person_id']:a for a in json.loads((root/'actors.json').read_text())}
    observations={};counts=Counter();positions=defaultdict(dict);role_conflicts=0
    visible_cameras=defaultdict(set);trajectory_checks=0

    with (root/'observations.jsonl').open() as f:
        for line in f:
            record=json.loads(line);cam=record['camera_id'];fi=record['frame_index']
            assert abs(record['source_time_seconds']-fi/fps)<1e-8
            counts[cam]+=1
            if fi==220:observations[(cam,fi)]=record['people']
            for actor in record['people']:
                actor_id=actor['person_id'];reference_actor=actor_registry[actor_id]
                assert actor['role']==reference_actor['role'],(actor_id,'role mismatch')
                path=reference_actor['waypoints'];t=fi/fps
                times=[point['time_seconds'] for point in path]
                segment=min(len(path)-2,max(0,int(np.searchsorted(times,t,side='right')-1)))
                a,b=path[segment],path[segment+1]
                fraction=np.clip((t-a['time_seconds'])/(b['time_seconds']-a['time_seconds']),0,1)
                xy=[a['x_m']+fraction*(b['x_m']-a['x_m']),a['y_m']+fraction*(b['y_m']-a['y_m'])]
                assert np.allclose(actor['world_position_m'],xy,atol=.00006,rtol=0),(actor_id,fi,'trajectory mismatch')
                x0,y0,x1,y1=actor['bbox_xyxy']
                assert 0<=x0<x1<=manifest['cameras'][0]['resolution'][0]
                assert 0<=y0<y1<=manifest['cameras'][0]['resolution'][1]
                visible_cameras[actor_id].add(cam);trajectory_checks+=1
                key=(fi,actor_id);value=(actor['world_position_m'],actor['role'])
                if key in positions and positions[key]!=value:role_conflicts+=1
                positions[key]=value
    assert len(counts)==8 and all(v==expected for v in counts.values()),counts
    assert role_conflicts==0,'Different cameras disagree about shared actors'
    for t in [0,22,45,59.9]:
        frame=snapshot(root/'security_monitor_8cams.mp4',min(t,manifest['duration_seconds']-.1))
        cv2.imwrite(str(root/f'preview_{str(t).replace(".","_")}s.jpg'),frame)
    report=dict(overall_pass=True,camera_count=8,duration_seconds=manifest['duration_seconds'],
        fps=fps,shared_frames=expected,all_videos_decoded=True,
        all_frame_timestamps_identical=True,cross_camera_world_state_consistent=True,
        annotation_rows=sum(counts.values()),files=results)
    assert set(visible_cameras)==set(actor_registry),'Some scripted actors were never visible'
    report['ground_truth_trajectory_checks']=trajectory_checks
    report['all_20_actors_visible']=True
    report['cameras_observing_each_actor']={pid:sorted(cams) for pid,cams in sorted(visible_cameras.items())}
    uniform_records=[]
    for camera_index in range(1,9):
        camera_id=f'cam{camera_index:02d}'
        frame=snapshot(root/f'{camera_id}.mp4',22)
        for person in observations[(camera_id,220)]:
            if person['person_id'] not in [f'E{camera_index:02d}',f'C{camera_index:02d}']:continue
            x0,y0,x1,y1=person['bbox_xyxy']
            torso=frame[y0+int((y1-y0)*.12):y0+int((y1-y0)*.65),x0:x1]
            mask=cv2.inRange(cv2.cvtColor(torso,cv2.COLOR_BGR2HSV),np.array([2,145,105]),np.array([25,255,255]))
            fraction=float(np.count_nonzero(mask)/mask.size)
            uniform_records.append(dict(camera_id=camera_id,person_id=person['person_id'],
                role=person['role'],orange_torso_fraction=round(fraction,4),
                color_matches_fixture=(fraction>.07)==(person['role']=='employee')))
    report['fixture_uniform_check']={
        'time_seconds':22,'records':uniform_records,
        'all_pass':len(uniform_records)==16 and all(r['color_matches_fixture'] for r in uniform_records),
        'note':'Known simulation boxes, not automatic detection or a training benchmark.'}
    if args.model:
        report['yolo_smoke_check']=detector_check(root,args.model,observations)
        print(json.dumps(report['yolo_smoke_check']['totals']),flush=True)
    (root/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Verified all 9 videos, frame timestamps, and shared actor states.',flush=True)


if __name__=='__main__':main()
