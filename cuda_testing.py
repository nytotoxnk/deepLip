import torch

if torch.cuda.is_available():
    print("CUDA is available!")
    print(f"Number of GPUs: {torch.cuda.device_count()}")
    print(f"Current GPU: {torch.cuda.get_device_name(0)}")
else:
    print("CUDA is not available. PyTorch will use CPU.")

# You can also get more details if CUDA is available:
if torch.cuda.is_available():
    device = torch.device("cuda")
    print(f"Device properties: {torch.cuda.get_device_properties(device)}")