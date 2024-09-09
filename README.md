# Archive Tools for WAIVE-FRONT

Use these tools to prepare your archive for use in WAIVE-FRONT.

# Dependencies
Tested with `python==3.10`

`main.py`:

```
tqdm==4.66.4
```

`server.py`:
```
pytorch==2.3.1
pytorch-cuda=12.1
torchvision==0.18.1
transformers==4.40.2
pillow=10.3.0
```

# Usage
First, make sure all dependencies are installed. On the computer with a CUDA-enabled graphics card, make sure `server.py` is running. Then, on the computer containing the material, run `main.py`.

`main.py` takes two arguments. The first is the path to a folder that contains a `data.csv` file and a folder called `video` that contains .mp4 files. The second is the IP address of the computer that is running `server.py`. This can be the same computer.

It is crucial that the input is formatted exactly as in the example given. The folder name will be used as the name of the source, so make sure it is correct and only contains alphanumeric characters and underscores. `data.csv` must contain the columns as per the example.

When a video is done processing, it is appended to the output's `data.json`. Next time you run the script, it will check for existing id's in this file and skip them. This makes the process resumable. We recommend to test with a small batch first before commiting resources to a large library of videos.
