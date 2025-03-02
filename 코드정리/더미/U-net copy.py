# 1. 필요한 라이브러리 설치 및 임포트
import os
import cv2
import torch
import numpy as np
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms
import torch.nn as nn
import torch.optim as optim
import torchvision.models as models
from tqdm import tqdm
import albumentations as A
from albumentations.pytorch import ToTensorV2

# 2. CityscapesDataset 클래스 정의
class CityscapesDataset(Dataset):
    def __init__(self, images_dir, labels_dir, transform=None):
        self.images_dir = images_dir
        self.labels_dir = labels_dir
        self.transform = transform

        # 이미지 및 라벨 파일 목록 생성
        self.image_files = sorted(os.listdir(images_dir))
        self.label_files = sorted([
            f for f in os.listdir(labels_dir)
            if f.endswith('labelIds.png')  # 'labelIds.png' 파일만 포함
        ])

        # 이미지와 라벨 수 확인
        if len(self.image_files) != len(self.label_files):
            raise ValueError("이미지와 라벨의 수가 일치하지 않습니다.")

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        # 이미지 로드
        image_path = os.path.join(self.images_dir, self.image_files[idx])
        image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 라벨 로드
        label_path = os.path.join(self.labels_dir, self.label_files[idx])
        label = cv2.imread(label_path, cv2.IMREAD_GRAYSCALE)

        # 변환 적용
        if self.transform:
            augmented = self.transform(image=image, mask=label)
            image = augmented['image']
            label = augmented['mask']

        # 이미지와 라벨을 NCHW 형식으로 변환
        image = image.permute(0, 1, 2)  # HWC -> CHW
        label = label.unsqueeze(0)  # HWC -> CHW
        label = label.long()  # Byte tensor를 Long tensor로 변환

        # 레이블의 최소값과 최대값 확인
        #min_label = label.min().item()
        #max_label = label.max().item()
        #print(f"Label min: {min_label}, Label max: {max_label}")

        return image, label
class CityscapesDataset_Test(Dataset):
    def __init__(self, images_dir, labels_dir, transform=None):
        self.images_dir = images_dir
        self.labels_dir = labels_dir
        self.transform = transform
        
        # 이미지 및 라벨 파일 목록 생성
        self.image_files = sorted(os.listdir(images_dir))[:10]  # 처음 300개 샘플만 사용
        self.label_files = sorted([
            f for f in os.listdir(labels_dir)
            if f.endswith('labelIds.png')
        ])[:10]  # 처음 300개 샘플만 사용

        # 이미지와 라벨 수 확인
        if len(self.image_files) != len(self.label_files):
            raise ValueError("이미지와 라벨의 수가 일치하지 않습니다.")

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        # 이미지 로드
        image_path = os.path.join(self.images_dir, self.image_files[idx])
        image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 라벨 로드
        label_path = os.path.join(self.labels_dir, self.label_files[idx])
        label = cv2.imread(label_path, cv2.IMREAD_GRAYSCALE)

        # 변환 적용
        if self.transform:
            augmented = self.transform(image=image, mask=label)
            image = augmented['image']
            label = augmented['mask']

        # numpy에서 torch tensor로 변환
        image = torch.tensor(image).permute(2, 0, 1)  # HWC -> CHW
        label = torch.tensor(label).unsqueeze(0).long()  # HWC -> CHW

        return image, label
    
# 3. 데이터셋 경로 설정 (테스트셋 경로 추가)
train_images_dir = "dataset_city1/train/images"
train_labels_dir = "dataset_city1/train/labels"
val_images_dir = "dataset_city1/val/images"
val_labels_dir = "dataset_city1/val/labels"
test_images_dir = "dataset_city1/test/images"
test_labels_dir = "dataset_city1/test/labels"


# 4. 데이터셋 변환 및 데이터 로더 설정 (테스트셋에 대해 데이터로더 추가)
train_transform = A.Compose([
    A.Resize(height=256, width=512),
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ToTensorV2(),
])
val_transform = train_transform

train_dataset = CityscapesDataset(train_images_dir, train_labels_dir, transform=train_transform)
val_dataset = CityscapesDataset(val_images_dir, val_labels_dir, transform=val_transform)
test_dataset = CityscapesDataset_Test(test_images_dir, test_labels_dir, transform=val_transform)

train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True, num_workers=2)
val_loader = DataLoader(val_dataset, batch_size=8, shuffle=False, num_workers=2)
test_loader = DataLoader(test_dataset, batch_size=8, shuffle=False, num_workers=2)

# 5. U-Net 모델 정의
def conv_block(in_dim, out_dim, act_fn):
    model = nn.Sequential(
        nn.Conv2d(in_dim, out_dim, kernel_size=3, stride=1, padding=1),
        nn.BatchNorm2d(out_dim),
        act_fn,
    )
    return model

def conv_trans_block(in_dim, out_dim, act_fn):
    model = nn.Sequential(
        nn.ConvTranspose2d(in_dim, out_dim, kernel_size=3, stride=2, padding=1, output_padding=1),
        nn.BatchNorm2d(out_dim),
        act_fn,
    )
    return model

def maxpool():
    pool = nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
    return pool

def conv_block_2(in_dim, out_dim, act_fn):
    model = nn.Sequential(
        conv_block(in_dim, out_dim, act_fn),
        nn.Conv2d(out_dim, out_dim, kernel_size=3, stride=1, padding=1),
        nn.BatchNorm2d(out_dim),
    )
    return model

class UnetGenerator(nn.Module):
    def __init__(self, in_dim, out_dim, num_filter):
        super(UnetGenerator, self).__init__()
        act_fn = nn.LeakyReLU(0.2, inplace=True)

        self.down_1 = conv_block_2(in_dim, num_filter, act_fn)
        self.pool_1 = maxpool()
        self.down_2 = conv_block_2(num_filter, num_filter * 2, act_fn)
        self.pool_2 = maxpool()
        self.down_3 = conv_block_2(num_filter * 2, num_filter * 4, act_fn)
        self.pool_3 = maxpool()
        self.down_4 = conv_block_2(num_filter * 4, num_filter * 8, act_fn)
        self.pool_4 = maxpool()

        self.bridge = conv_block_2(num_filter * 8, num_filter * 16, act_fn)

        self.trans_1 = conv_trans_block(num_filter * 16, num_filter * 8, act_fn)
        self.up_1 = conv_block_2(num_filter * 16, num_filter * 8, act_fn)
        self.trans_2 = conv_trans_block(num_filter * 8, num_filter * 4, act_fn)
        self.up_2 = conv_block_2(num_filter * 8, num_filter * 4, act_fn)
        self.trans_3 = conv_trans_block(num_filter * 4, num_filter * 2, act_fn)
        self.up_3 = conv_block_2(num_filter * 4, num_filter * 2, act_fn)
        self.trans_4 = conv_trans_block(num_filter * 2, num_filter, act_fn)
        self.up_4 = conv_block_2(num_filter * 2, num_filter, act_fn)

        self.out = nn.Sequential(
            nn.Conv2d(num_filter, out_dim, kernel_size=3, stride=1, padding=1),
            nn.LogSoftmax(dim=1),  # LogSoftmax 사용
        )

    def forward(self, input):
        down_1 = self.down_1(input)
        pool_1 = self.pool_1(down_1)
        down_2 = self.down_2(pool_1)
        pool_2 = self.pool_2(down_2)
        down_3 = self.down_3(pool_2)
        pool_3 = self.pool_3(down_3)
        down_4 = self.down_4(pool_3)
        pool_4 = self.pool_4(down_4)

        bridge = self.bridge(pool_4)

        trans_1 = self.trans_1(bridge)
        concat_1 = torch.cat([trans_1, down_4], dim=1)
        up_1 = self.up_1(concat_1)
        trans_2 = self.trans_2(up_1)
        concat_2 = torch.cat([trans_2, down_3], dim=1)
        up_2 = self.up_2(concat_2)
        trans_3 = self.trans_3(up_2)
        concat_3 = torch.cat([trans_3, down_2], dim=1)
        up_3 = self.up_3(concat_3)
        trans_4 = self.trans_4(up_3)
        concat_4 = torch.cat([trans_4, down_1], dim=1)
        up_4 = self.up_4(concat_4)

        out = self.out(up_4)
        return out

# 6. 모델 초기화
n_classes = 34  # Cityscapes의 클래스 수
in_channels = 3  # 입력 이미지의 채널 수 (RGB)
num_filter = 64  # 필터 수

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = UnetGenerator(in_channels, n_classes, num_filter).to(device)  # 인자 추가

# 7. 손실 함수와 옵티마이저 설정
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)  # optimizer 정의

# 8. 학습 및 검증 루프
if __name__ == '__main__':
    n_epochs = 20
    for epoch in range(n_epochs):
        model.train()
        train_loss = 0
        for images, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{n_epochs}"):
            images, labels = images.to(device), labels.to(device)

            # 모델 예측
            outputs = model(images)
            loss = criterion(outputs, labels.squeeze(1))  # 채널 차원 제거
            train_loss += loss.item()

            # 역전파 및 가중치 업데이트
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        avg_train_loss = train_loss / len(train_loader)
        print(f"train_loss: {avg_train_loss:.4f}")

        # 검증 단계
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels.squeeze(1))
                val_loss += loss.item()

        avg_val_loss = val_loss / len(val_loader)
        print(f"val_loss: {avg_val_loss:.4f}")

        # 모델 저장
        torch.save(model.state_dict(), "unet_cityscapes.pth")
    # 테스트셋 평가 - 10장만 사용
    model.eval()
    test_loss = 0
    num_test_images = 10  # 평가할 테스트셋 이미지 수 설정

    
###RuntimeError: Given groups=1, weight of size [64, 3, 3, 3], expected input[8, 512, 3, 256] to have 3 channels, but got 512 channels instead
    with torch.no_grad():
        for idx, (images, labels) in enumerate(tqdm(test_loader, desc="Testing")):
            if idx >= num_test_images:  # 10장만 평가
                break

            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels.squeeze(1))
            test_loss += loss.item()

            # 예측 결과 시각화 (원본 이미지, 레이블, 예측 결과)
            _, predicted = torch.max(outputs, dim=1)  # 가장 높은 확률의 클래스 예측
            predicted = predicted.cpu().numpy().squeeze()
            labels = labels.cpu().numpy().squeeze()

            # 시각화
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(1, 3, figsize=(15, 5))
            ax[0].imshow(images.cpu().squeeze().permute(1, 2, 0).numpy())
            ax[0].set_title("Original Image")
            ax[1].imshow(labels, cmap="gray")
            ax[1].set_title("Ground Truth")
            ax[2].imshow(predicted, cmap="gray")
            ax[2].set_title("Prediction")
            plt.show()

    # 평균 테스트 손실 출력
    avg_test_loss = test_loss / num_test_images
    print(f"Test Loss (10 samples): {avg_test_loss:.4f}")

