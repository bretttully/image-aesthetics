# Getting up and running with TensorFlow

## Installation

- Get CUDA 7.5 from https://developer.nvidia.com/cuda-downloads
```bash
sudo apt install nvidia-cuda-toolkit
```

- Get cuDNN v4 from https://developer.nvidia.com/cudnn -- this will require signing 
up to the developer program. Use `locate cuda.h` and `locate libcuda.so` to find the 
right place to copy these. The following works on Ubuntu 16.04.
```bash
tar xvzf cudnn-7.*
sudo cp cuda/include/cudnn.h /usr/include/cuda
sudo cp cuda/lib64/libcudnn* /usr/lib/x86_64-linux-gnu/
sudo chmod a+r /usr/include/cudnn.h /usr/lib/x86_64-linux-gnu/libcudnn*
```

- Install using conda
```bash
conda create -n tensorflow-gpu python=3.5 anaconda
source activate tensorflow-gpu
pip install jupyter pandas tables matplotlib
export TF_BINARY_URL=https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow-0.10.0rc0-cp35-cp35m-linux_x86_64.whl
pip install --ignore-installed --upgrade ${TF_BINARY_URL}
```

- Test that the install has been successful
```bash
python -c "import tensorflow"
```

- Install `bazel`: see [here](http://www.bazel.io/versions/master/docs/install.html#install-on-ubuntu)
```bash
echo "deb [arch=amd64] http://storage.googleapis.com/bazel-apt stable jdk1.8" | sudo tee /etc/apt/sources.list.d/bazel.list
curl https://storage.googleapis.com/bazel-apt/doc/apt-key.pub.gpg | sudo apt-key add -
sudo apt update
sudo apt install bazel swig
```
