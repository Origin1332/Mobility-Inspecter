"""Validate reviewed annotations and create a reproducible YOLO split."""
import argparse, collections, hashlib, json, math, random, shutil, zipfile
from pathlib import Path
from PIL import Image

CLASSES = ["headlight_left","headlight_right","radiator_grille","front_bumper","windshield","fog_light","hood","front_fender_left","front_fender_right","windshield_wiper"]

def convert(source, output, seed=42):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError("Output already exists; choose a new directory to avoid stale labels")
    with zipfile.ZipFile(source) as z:
        annotations = [n for n in z.namelist() if n.endswith("/annotations.json") or n == "annotations.json"]
        if len(annotations) != 1:
            raise ValueError("Exactly one annotations.json is required")
        annotation_path = Path(annotations[0])
        doc = json.loads(z.read(annotations[0]).decode("utf-8-sig"))
        if doc["classes"] != CLASSES:
            raise ValueError("Class order differs from the reviewed front-parts contract")
        records, hashes, names = [], set(), set()
        counts = collections.Counter()
        for row in doc["images"]:
            name = row["file_name"]
            if Path(name).name != name or "/" in name or "\\" in name or name in names:
                raise ValueError("Unsafe or duplicate image filename")
            names.add(name)
            raw = z.read((annotation_path.parent / "images" / name).as_posix())
            import io
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                w, h = image.size
                if (w, h) != (row["width"], row["height"]):
                    raise ValueError(f"Image size mismatch: {name}")
                if image.format != "JPEG":
                    raise ValueError("Expected JPEG images")
            digest = hashlib.sha256(raw).hexdigest()
            if digest in hashes:
                raise ValueError(f"Duplicate image: {name}; resolve before splitting")
            hashes.add(digest)
            lines = []
            for obj in row["objects"]:
                cid = CLASSES.index(obj["class"])
                x1,y1,x2,y2 = obj["bbox"]
                if not all(math.isfinite(v) for v in (x1,y1,x2,y2)) or not (0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h):
                    raise ValueError(f"Invalid bounding box: {name}")
                lines.append(f"{cid} {(x1+x2)/2/w:.8f} {(y1+y2)/2/h:.8f} {(x2-x1)/w:.8f} {(y2-y1)/h:.8f}")
                counts[obj["class"]] += 1
            records.append((name,raw,lines))
    if len(records) < 2:
        raise ValueError("At least two distinct images are required")
    random.Random(seed).shuffle(records)
    nval = max(1, round(len(records)*0.2))
    splits = {"val": records[:nval], "train": records[nval:]}
    distribution = {}
    for split, entries in splits.items():
        (output / "images" / split).mkdir(parents=True)
        (output / "labels" / split).mkdir(parents=True)
        counter = collections.Counter()
        for name,raw,lines in entries:
            (output/"images"/split/name).write_bytes(raw)
            (output/"labels"/split/Path(name).with_suffix(".txt")).write_text("\n".join(lines)+"\n",encoding="utf-8")
            counter.update(CLASSES[int(line.split()[0])] for line in lines)
        distribution[split] = {c: counter[c] for c in CLASSES}
    # JSON values are valid YAML scalars/arrays.
    yaml = f"path: {json.dumps(output.resolve().as_posix())}\ntrain: images/train\nval: images/val\nnames: {json.dumps(CLASSES)}\n"
    (output/"data.yaml").write_text(yaml,encoding="utf-8")
    report = {"source":source.name,"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"seed":seed,
              "images":len(records),"boxes":sum(counts.values()),"classes":CLASSES,
              "counts":{c:counts[c] for c in CLASSES},"splits":{k:[r[0] for r in v] for k,v in splits.items()},
              "split_counts":distribution,"untrained_classes":[c for c in CLASSES if not distribution["train"][c]],
              "warning":"Small dataset; validation is a smoke check, not evidence of field accuracy. Review near-duplicate vehicles before production."}
    (output/"dataset_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    return report

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True); p.add_argument("--output",required=True); p.add_argument("--seed",type=int,default=42)
    a=p.parse_args()
    print(json.dumps(convert(a.source,a.output,a.seed),indent=2,ensure_ascii=False))
