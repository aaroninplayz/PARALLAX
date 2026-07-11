import torch
import torch.nn as nn

class ConvAutoencoder(nn.Module):
    def __init__(self):
        super(ConvAutoencoder, self).__init__()
        
        # Encoder (Compresses 128x128 RGB image into a compressed spatial tensor)
        self.encoder = nn.Sequential(
            # Input: [Batch, 3, 128, 128]  (RGB color)
            nn.Conv2d(3, 16, 3, stride=2, padding=1),  # -> [16, 64, 64]
            nn.LeakyReLU(0.2),
            nn.Conv2d(16, 32, 3, stride=2, padding=1), # -> [32, 32, 32]
            nn.LeakyReLU(0.2),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), # -> [64, 16, 16]
            nn.LeakyReLU(0.2),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),# -> [128, 8, 8]
            nn.LeakyReLU(0.2)
        )
        
        # Decoder (Attempts to rebuild the 128x128 image from the compressed spatial tensor)
        self.decoder = nn.Sequential(
            # Input: [128, 8, 8]
            nn.ConvTranspose2d(128, 64, 3, stride=2, padding=1, output_padding=1), # -> [64, 16, 16]
            nn.LeakyReLU(0.2),
            nn.ConvTranspose2d(64, 32, 3, stride=2, padding=1, output_padding=1),  # -> [32, 32, 32]
            nn.LeakyReLU(0.2),
            nn.ConvTranspose2d(32, 16, 3, stride=2, padding=1, output_padding=1),  # -> [16, 64, 64]
            nn.LeakyReLU(0.2),
            nn.ConvTranspose2d(16, 3, 3, stride=2, padding=1, output_padding=1),   # -> [3, 128, 128]  (RGB output)
            nn.Sigmoid() # Force output pixel values to float ranges [0.0, 1.0]
        )

    def forward(self, x):
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return reconstructed

class DifferenceClassifier(nn.Module):
    def __init__(self):
        super(DifferenceClassifier, self).__init__()
        import torchvision.models as models
        # Using ResNet-18 as the large classification model
        self.model = models.resnet18(weights=None)
        
        # ResNet-18 natively accepts 3-channel RGB input — no modification needed.
        # self.model.conv1 is already Conv2d(3, 64, ...) by default.
        
        # Modify the final fully connected layer for binary classification:
        # Output is a single value representing the probability of True Anomaly.
        num_ftrs = self.model.fc.in_features
        self.model.fc = nn.Sequential(
            nn.Linear(num_ftrs, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.model(x)
