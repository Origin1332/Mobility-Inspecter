"""Train locally and export a validated Android model package."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",required=True)
    p.add_argument("--weights",default="yolov8n.pt",help="Local pretrained weights; downloads require Internet")
    p.add_argument("--epochs",type=int,default=100)
    p.add_argument("--device",default="cpu")
    p.add_argument("--output",default="models/front-parts")
    p.add_argument("--checkpoint",help="Export an existing trained checkpoint without training")
    a=p.parse_args()
    from ultralytics import YOLO
    import onnx, onnxruntime as ort, numpy as np, yaml
    from prepare_dataset import CLASSES
    data=yaml.safe_load(Path(a.data).read_text(encoding="utf-8"))
    if data["names"] != CLASSES: raise ValueError("Dataset class order mismatch")
    if a.checkpoint:
        model=YOLO(a.checkpoint)
    else:
        model=YOLO(a.weights)
        model.train(data=str(Path(a.data).resolve()),epochs=a.epochs,imgsz=640,batch=4,device=a.device,
                    seed=42,deterministic=True,fliplr=0.0,flipud=0.0,workers=0,
                    project="runs",name="front-parts",exist_ok=False)
        model=YOLO(model.trainer.best)
    names=[model.names[i] for i in range(len(model.names))]
    if names != CLASSES: raise ValueError("Trained model class order mismatch")
    exported=Path(model.export(format="onnx",imgsz=640,batch=1,dynamic=False,simplify=False,
                               opset=17,half=False,nms=False,device="cpu"))
    onnx.checker.check_model(onnx.load(str(exported)))
    session=ort.InferenceSession(str(exported),providers=["CPUExecutionProvider"])
    x=np.zeros((1,3,640,640),dtype=np.float32)
    pred=session.run(None,{session.get_inputs()[0].name:x})[0]
    if pred.shape != (1,14,8400) or not np.isfinite(pred).all():
        raise ValueError(f"Unsupported output: {pred.shape}")
    output=Path(a.output); output.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(exported,output/"model.onnx")
    manifest={"schema_version":1,"architecture":"yolov8","input_size":640,"classes":names,
              "sha256":hashlib.sha256((output/"model.onnx").read_bytes()).hexdigest(),
              "description":"Vehicle front parts; detection only, no damage diagnosis"}
    (output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    with zipfile.ZipFile(output.with_suffix(".zip"),"w",zipfile.ZIP_DEFLATED) as z:
        for name in ("model.onnx","manifest.json"): z.write(output/name,name)
    print(output.with_suffix(".zip").resolve())

if __name__ == "__main__": main()
