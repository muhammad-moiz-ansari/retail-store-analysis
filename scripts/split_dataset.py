# Detector split by recording (no recording in two splits). Source: ~/data/cvat_prelabels (CVAT YOLO export).
# Output: ~/data/split/{train,val,test} + split_manifest.csv (committed copy: data/split/split_manifest.csv).
import re, random, shutil, csv, zipfile
from pathlib import Path
from collections import defaultdict, Counter

SRC = Path.home() / 'data' / 'cvat_prelabels'
OUT = Path.home() / 'data' / 'split'
RATIOS = {'train': 0.70, 'val': 0.15, 'test': 0.15}
SEED = 0

imgs = sorted((SRC / 'obj_train_data').glob('*.jpg'))
pat = re.compile(r'^(?P<rec>.+?)_part\d+_sq640_\d+$')
groups = defaultdict(list)
for p in imgs:
    m = pat.match(p.stem)
    rec = m.group('rec') if m else p.stem.rsplit('_', 1)[0]
    groups[rec].append(p)

total = len(imgs)
target = {k: v * total for k, v in RATIOS.items()}
assigned = {k: [] for k in RATIOS}
count = {k: 0 for k in RATIOS}

recs = list(groups)
random.Random(SEED).shuffle(recs)
recs.sort(key=lambda r: -len(groups[r]))          # place big recordings first, then fill gaps
for r in recs:
    split = max(RATIOS, key=lambda k: target[k] - count[k])   # biggest remaining deficit
    assigned[split].append(r)
    count[split] += len(groups[r])

names = (SRC / 'obj.names').read_text()
if OUT.exists():
    shutil.rmtree(OUT)
manifest = []

for split, rec_list in assigned.items():
    pkg = OUT / split
    (pkg / 'obj_train_data').mkdir(parents=True)
    (pkg / 'obj.names').write_text(names)
    (pkg / 'obj.data').write_text('classes = 2\ntrain = train.txt\nnames = obj.names\nbackup = backup/\n')
    lines, boxes = [], Counter()
    for r in rec_list:
        for p in groups[r]:
            lab = p.with_suffix('.txt')
            shutil.copy(p, pkg / 'obj_train_data' / p.name)
            shutil.copy(lab, pkg / 'obj_train_data' / lab.name)
            lines.append(f'data/obj_train_data/{p.name}')
            for ln in lab.read_text().splitlines():
                if ln.strip():
                    boxes[ln.split()[0]] += 1
            manifest.append((p.name, r, split))
    (pkg / 'train.txt').write_text('\n'.join(lines) + '\n')
    zpath = OUT / f'{split}.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_STORED) as z:
        for f in pkg.rglob('*'):
            if f.is_file():
                z.write(f, f.relative_to(pkg))
    print(f'{split:5s} recordings={len(rec_list):3d} frames={len(lines):5d} '
          f'employee={boxes["0"]:5d} customer={boxes["1"]:5d}  -> {zpath}')

with open(OUT / 'split_manifest.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['image', 'recording', 'split']); w.writerows(manifest)
print('manifest:', OUT / 'split_manifest.csv')
