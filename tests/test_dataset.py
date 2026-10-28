import io,json,tempfile,unittest,zipfile,sys
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from prepare_dataset import convert,CLASSES

class DatasetTests(unittest.TestCase):
    def fixture(self,folder,invalid=False,duplicate=False):
        path=Path(folder)/"source.zip"
        rows=[]
        with zipfile.ZipFile(path,"w") as z:
            for i in range(5):
                b=io.BytesIO()
                Image.new("RGB",(100,50),(0 if duplicate else i*40,0,0)).save(b,format="JPEG")
                name=f"{i}.jpg"; z.writestr("dataset/images/"+name,b.getvalue())
                rows.append({"file_name":name,"width":100,"height":50,"objects":[{"class":CLASSES[0],"bbox":[0,0,101 if invalid else 100,50]}]})
            z.writestr("dataset/annotations.json",json.dumps({"classes":CLASSES,"images":rows}))
        return path
    def test_normalization_split_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as d:
            source=self.fixture(d)
            a=convert(source,Path(d)/"a")
            b=convert(source,Path(d)/"b")
            self.assertEqual(a["splits"],b["splits"])
            self.assertFalse(set(a["splits"]["train"]) & set(a["splits"]["val"]))
            label=next((Path(d)/"a/labels/train").glob("*.txt")).read_text().split()
            self.assertEqual([float(v) for v in label[1:]],[.5,.5,1.,1.])
            self.assertIn("fog_light",a["untrained_classes"])
    def test_invalid_box_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): convert(self.fixture(d,invalid=True),Path(d)/"out")
            self.assertFalse((Path(d)/"out").exists())
    def test_duplicate_image_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): convert(self.fixture(d,duplicate=True),Path(d)/"out")
    def test_existing_destination_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): convert(self.fixture(d),d)
if __name__=="__main__": unittest.main()
