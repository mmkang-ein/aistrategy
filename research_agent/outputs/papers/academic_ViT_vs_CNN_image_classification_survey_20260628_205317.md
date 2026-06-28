# ViT vs CNN Image Classification Survey: AGSR Framework for Enhancing CNN OOD Robustness via Shape-Consistency Alignment

---

## Abstract

Vision Transformer(ViT)와 CNN은 이미지 분류에서 각각 고유한 귀납적 편향을 가지며 상이한 강점을 보인다. 본 논문은 두 패러다임을 체계적으로 비교·분석하고, ViT의 전역적 형태 편향이 OOD(Out-of-Distribution) 견고성 우위의 핵심 인과 요인임을 Stylized ImageNet 개입 실험으로 검증한다. 이를 기반으로 세그멘테이션 마스크 기반 객체 경계 일치도를 정렬 신호로 활용하는 **AGSR(Attention-Guided Shape Regularization)** 프레임워크를 제안한다. AGSR은 아키텍처 변경 없이 CNN의 OOD 견고성을 향상시키며, 오프라인 캐싱 기반 효율적 증류로 학습 오버헤드를 10% 이하로 유지한다.

**Keywords:** Vision Transformer, CNN, OOD Robustness, Shape Bias, Knowledge Distillation, Attention Alignment, Image Classification

---

## 1. Introduction

### 1.1 연구 배경 및 동기

딥러닝 기반 이미지 분류는 지난 10여 년간 Convolutional Neural Network(CNN)이 주도해왔다. AlexNet(Krizhevsky et al., 2012)을 시작으로 VGGNet, ResNet, EfficientNet 등 일련의 CNN 아키텍처는 ImageNet을 비롯한 다양한 벤치마크에서 지속적인 성능 향상을 이끌었다. CNN의 핵심 설계 원리인 **지역적 수용 영역(local receptive field)**, **가중치 공유(weight sharing)**, **공간적 계층 구조(spatial hierarchy)**는 이미지의 국소 패턴을 효율적으로 포착하는 강력한 귀납적 편향(inductive bias)으로 작용한다.

그러나 2020년 Dosovitskiy et al.이 제안한 **Vision Transformer(ViT)**는 이미지를 패치 시퀀스로 분할하고 자기주의(self-attention) 메커니즘을 적용함으로써 CNN의 패러다임에 근본적인 도전을 제기하였다. ViT는 대규모 데이터셋(JFT-300M 등)으로 사전학습 시 CNN을 능가하는 성능을 보였으며, 이후 DeiT, Swin Transformer, CvT 등 다양한 변형 모델이 등장하며 컴퓨터 비전의 새로운 주류로 자리잡았다.

두 패러다임의 가장 두드러진 차이 중 하나는 **분포 외(OOD) 견고성**이다. Geirhos et al.(2019)의 연구는 CNN이 이미지의 형태(shape)보다 텍스처(texture)에 과도하게 의존하는 반면, ViT는 전역적 자기주의를 통해 형태 중심의 표현을 학습함을 보였다. 이 차이는 ImageNet-C(부패 견고성), ImageNet-R(렌더링 견고성), ImageNet-Sketch 등의 OOD 벤치마크에서 ViT의 일관된 우위로 이어진다.

그러나 실무 환경에서는 다음과 같은 현실적 제약이 존재한다:

1. **데이터 효율성**: ViT는 대규모 사전학습 데이터 없이는 CNN 대비 열등한 성능을 보인다.
2. **계산 효율성**: ViT의 자기주의 연산은 시퀀스 길이에 대해 이차적 복잡도를 가지며, 엣지 디바이스 배포에 불리하다.
3. **아키텍처 전환 비용**: 기존 CNN 기반 파이프라인을 ViT로 전환하는 것은 상당한 엔지니어링 비용을 수반한다.

이러한 맥락에서 **"아키텍처를 변경하지 않고 CNN에 ViT의 OOD 견고성을 이식할 수 있는가?"**라는 질문이 자연스럽게 제기된다. 본 논문은 이 질문에 답하기 위해 다음의 연구를 수행한다.

### 1.2 연구 동기: 형태 편향과 OOD 견고성의 인과 관계

기존 연구들은 ViT의 OOD 우위와 형태 편향 사이의 **상관 관계**를 보고하였으나, 이 관계의 **인과성**을 엄밀히 검증한 연구는 드물다. 본 연구는 Stylized ImageNet을 활용한 개입 실험(intervention experiment)을 통해 "형태 편향 → OOD 견고성"의 인과 관계를 선행 검증하고, 이를 기반으로 AGSR 프레임워크의 이론적 토대를 구축한다.

```
[인과 가설 다이어그램]

형태 편향 증가
     │
     ▼
전역적 의미 표현 학습
     │
     ▼
텍스처/스타일 변화에 불변한 특징 추출
     │
     ▼
OOD 견고성 향상
(ImageNet-C/R/Sketch)
```

### 1.3 핵심 기여 (Contributions)

본 논문의 주요 기여는 다음과 같다:

1. **체계적 비교 분석**: ViT와 CNN을 정확도, 계산 효율성, 데이터 효율성, OOD 견고성, 해석 가능성의 5개 축에서 포괄적으로 비교하는 서베이를 제공한다.

2. **인과성 검증**: Stylized ImageNet 개입 실험을 통해 형태 편향과 OOD 견고성 사이의 인과 관계를 실험적으로 확립한다.

3. **AGSR 프레임워크 제안**: 세그멘테이션 마스크 기반 객체 경계 일치도를 정렬 신호로 사용하여 ViT의 형태 편향을 CNN에 이식하는 새로운 정규화 방법론을 제안한다.

4. **효율적 오프라인 증류**: GSCS(Global Shape Consistency Score) 사전 계산 및 캐싱을 통해 학습 오버헤드를 기준 대비 10% 이하로 유지하는 실용적 구현 전략을 제시한다.

5. **다양한 도메인 검증**: 자연 이미지(ImageNet), 의료 영상(NIH ChestX-ray), 자율주행(Cityscapes) 등 다양한 도메인에서 AGSR의 효과를 검증한다.

---

## 2. Related Work

### 2.1 CNN 기반 이미지 분류

CNN은 LeNet(LeCun et al., 1998)에서 시작하여 AlexNet(2012), VGGNet(Simonyan & Zisserman, 2014), GoogLeNet(Szegedy et al., 2015), ResNet(He et al., 2016), DenseNet(Huang et al., 2017), EfficientNet(Tan & Le, 2019), ConvNeXt(Liu et al., 2022)에 이르기까지 지속적으로 발전하였다.

**ResNet**은 잔차 연결(residual connection)을 도입하여 깊은 네트워크의 학습 안정성을 확보하였으며, ImageNet에서 top-1 정확도 76.1%를 달성하였다. **EfficientNet**은 복합 스케일링(compound scaling)을 통해 파라미터 효율성을 극대화하였다. **ConvNeXt**는 ViT의 설계 원리를 CNN에 도입하여 순수 CNN 아키텍처의 성능 한계를 재정의하였다.

CNN의 핵심 귀납적 편향은 다음과 같다:
- **지역성(Locality)**: 컨볼루션 필터는 국소 영역의 패턴을 포착한다.
- **평행 이동 불변성(Translation Invariance)**: 풀링 연산을 통해 위치 변화에 강건하다.
- **계층적 특징 추출(Hierarchical Feature Extraction)**: 낮은 층에서 엣지·텍스처, 높은 층에서 의미적 특징을 학습한다.

### 2.2 Vision Transformer 및 변형 모델

**ViT(Dosovitskiy et al., 2020)**는 이미지를 16×16 패치로 분할하고 Transformer 인코더를 적용한 최초의 순수 Transformer 기반 이미지 분류 모델이다. 대규모 데이터(JFT-300M)로 사전학습 시 ImageNet에서 88.55%의 top-1 정확도를 달성하였다.

**DeiT(Touvron et al., 2021)**는 지식 증류와 데이터 증강을 활용하여 ImageNet만으로 ViT를 효율적으로 학습하는 방법을 제시하였다. **Swin Transformer(Liu et al., 2021)**는 이동 창(shifted window) 메커니즘을 도입하여 계층적 특징 추출과 선형 복잡도를 달성하였다. **CvT(Wu et al., 2021)**는 컨볼루션 임베딩을 Transformer에 통합하여 하이브리드 접근법을 취하였다.

| 모델 | 파라미터 | ImageNet Top-1 | 특징 |
|------|----------|----------------|------|
| ViT-B/16 | 86M | 81.8% | 순수 Transformer |
| DeiT-B | 86M | 81.8% | 효율적 학습 |
| Swin-B | 88M | 83.5% | 계층적 구조 |
| ResNet-50 | 25M | 76.1% | 표준 CNN |
| ConvNeXt-B | 89M | 83.8% | 현대화된 CNN |
| EfficientNet-B7 | 66M | 84.3% | 복합 스케일링 |

### 2.3 하이브리드 아키텍처

CNN과 ViT의 상호 보완적 특성을 결합한 하이브리드 아키텍처가 활발히 연구되고 있다. **CoAtNet(Dai et al., 2021)**은 컨볼루션과 자기주의를 계층별로 결합하여 ImageNet에서 90.88%의 최고 성능을 달성하였다. **MobileViT(Mehta & Rastegari, 2021)**는 경량 CNN과 ViT를 결합하여 모바일 환경에서의 효율성을 확보하였다. **CMT(Guo et al., 2022)**는 CNN의 지역 특징 추출과 Transformer의 전역 모델링을 통합하였다.

### 2.4 OOD 견고성 및 형태 편향 연구

**Geirhos et al.(2019)**는 CNN이 텍스처에 강하게 편향되어 있음을 Stylized ImageNet 실험으로 입증하고, 형태 편향이 OOD 견고성과 상관관계를 가짐을 보였다. **Bhojanapalli et al.(2021)**는 ViT가 CNN 대비 자연 부패(natural corruption)에 더 강건함을 체계적으로 분석하였다. **Mao et al.(2022)**는 적절한 학습 전략 하에서 CNN도 ViT와 경쟁할 수 있는 적대적 견고성을 달성할 수 있음을 보였다.

### 2.5 지식 증류 및 어텐션 전달

**Hinton et al.(2015)**의 지식 증류(Knowledge Distillation, KD)는 교사 모델의 소프트 레이블을 활용하여 학생 모델을 학습시키는 방법론이다. **Zagoruyko & Komodakis(2017)**의 Attention Transfer(AT)는 교사 모델의 중간층 activation 통계를 학생 모델로 전달한다. **Park et al.(2019)**의 RKD와 **Peng et al.(2019)**의 PKT는 관계적 지식을 전달하는 방법을 제안하였다.

### 2.6 본 연구와의 차별점

기존 연구와 본 연구의 주요 차별점은 다음 표에 정리된다:

| 방법론 | 정렬 신호 | 의미론적 수준 | 인과성 검증 | 효율성 |
|--------|-----------|---------------|-------------|--------|
| AT (Zagoruyko, 2017) | Activation norm | 저수준 통계 | ✗ | 높음 |
| RKD (Park, 2019) | 관계적 거리 | 중간 수준 | ✗ | 중간 |
| KD (Hinton, 2015) | 소프트 레이블 | 출력 수준 | ✗ | 높음 |
| **AGSR (본 연구)** | **객체 경계 IoU** | **고수준 의미** | **✓** | **높음** |

AGSR의 핵심 차별성은 (1) 세그멘테이션 마스크 기반 **의미론적 고수준 신호**를 정렬 목표로 사용하고, (2) 형태 편향과 OOD 견고성의 **인과 관계를 선행 검증**하며, (3) **오프라인 캐싱**으로 실용적 효율성을 확보한다는 점이다.

---

## 3. Methodology

### 3.1 전체 프레임워크 개요

AGSR(Attention-Guided Shape Regularization) 프레임워크는 다음 세 가지 핵심 모듈로 구성된다:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGSR Framework Overview                       │
│                                                                   │
│  ┌──────────┐    ┌─────────────────┐    ┌────────────────────┐  │
│  │ 교사 ViT  │───▶│  GSCS 사전 계산  │───▶│   오프라인 캐시     │  │
│  │(동결됨)   │    │  (훈련 전 1회)   │    │  (디스크 저장)     │  │
│  └──────────┘    └─────────────────┘    └────────────────────┘  │
│                                                  │               │
│  ┌──────────┐    ┌─────────────────┐            │               │
│  │학생 CNN   │───▶│  Spatial Attn   │            │               │
│  │(ResNet-50)│    │  Map (CBAM 스타일)│            ▼               │
│  └──────────┘    └─────────────────┘    ┌────────────────────┐  │
│                           │              │   SAM-tiny 투영     │  │
│                           ▼              │  (객체 경계 마스크)  │  │
│                  ┌─────────────────┐    └────────────────────┘  │
│                  │  L_AGSR 계산     │◀───────────┘               │
│                  │ (Soft-IoU/코사인) │                            │
│                  └─────────────────┘                            │
│                           │                                      │
│                           ▼                                      │
│              L_total = L_CE + λ₁·L_AGSR + λ₂·L_KD              │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 인과성 검증 선행 실험

#### 3.2.1 실험 설계

"형태 편향 → OOD 견고성"의 인과 관계를 검증하기 위해 다음의 개입 실험을 수행한다:

**개입 변수**: ResNet-50의 형태 편향 수준 (Stylized ImageNet 파인튜닝 비율로 조절)

**결과 변수**: ImageNet-C mCE, ImageNet-R 정확도, ImageNet-Sketch 정확도

**실험 조건**:
- 조건 A: 표준 ImageNet 학습 (기준선)
- 조건 B: Stylized ImageNet 10% 혼합 파인튜닝
- 조건 C: Stylized ImageNet 50% 혼합 파인튜닝
- 조건 D: Stylized ImageNet 100% 파인튜닝

형태 편향 측정은 Geirhos et al.(2019)의 cue-conflict 자극(텍스처와 형태가 상충하는 합성 이미지)을 활용하여 모델의 형태 선택 비율(shape bias ratio)로 정량화한다.

**사전 설계된 대응 계획**: 만약 형태 편향 증가가 OOD 성능 향상으로 이어지지 않을 경우, (1) 주파수 특성(고주파 텍스처 억제) 또는 (2) 표현의 텍스처 불변성을 대안 메커니즘으로 분석하는 해석 프레임워크로 전환한다.

### 3.3 공통 의미 공간 설계

#### 3.3.1 이질성 문제 해결

Grad-CAM(CNN)과 ViT Attention Rollout(ViT)은 생성 메커니즘과 의미론적 수준이 상이하여 직접 비교가 어렵다. 본 연구는 두 가지 대안적 정렬 방법을 제안하고 비교한다.

**방법 A: 세그멘테이션 마스크 기반 IoU 정렬**

사전 학습된 경량 세그멘테이션 모델(SAM-tiny)을 활용하여 CNN의 Spatial Attention Map과 ViT의 CLS 토큰 어텐션 맵을 각각 객체 경계 일치 마스크로 투영한다.

$$M^{CNN} = \text{SAM-tiny}(\text{Grad-CAM}(f_{CNN}(x)))$$
$$M^{ViT} = \text{SAM-tiny}(\text{AttRollout}(f_{ViT}(x)))$$

**Soft-IoU 손실** (미분 불연속 문제 해결):

$$L_{AGSR}^{IoU} = 1 - \frac{\sum_{i,j} M^{CNN}_{ij} \cdot M^{ViT}_{ij} + \epsilon}{\sum_{i,j} (M^{CNN}_{ij} + M^{ViT}_{ij} - M^{CNN}_{ij} \cdot M^{ViT}_{ij}) + \epsilon}$$

여기서 $\epsilon = 10^{-6}$은 수치 안정성을 위한 스무딩 항이며, 마스크 값은 $[0, 1]$ 범위의 연속 확률값으로 처리하여 미분 가능성을 확보한다. 이는 표준 이진 IoU의 계단 함수 문제를 해결하며, Dice Loss와 동등한 최적화 특성을 가진다.

**방법 B: Spatial Attention 코사인 유사도 정렬**

CNN의 Feature Map 기반 Spatial Attention Map(CBAM 스타일)과 ViT의 CLS 토큰 어텐션 맵을 공통 정규화 공간에서 정렬한다.

$$A^{CNN} = \sigma\left(\text{MLP}\left(\text{AvgPool}(F^{CNN}) \oplus \text{MaxPool}(F^{CNN})\right)\right)$$
$$A^{ViT} = \text{Normalize}\left(\text{AttRollout}_{L}(f_{ViT}(x))\right)$$

$$L_{AGSR}^{cos} = 1 - \frac{\text{vec}(A^{CNN}) \cdot \text{vec}(A^{ViT})}{\|\text{vec}(A^{CNN})\| \cdot \|\text{vec}(A^{ViT})\|}$$

여기서 $\text{vec}(\cdot)$은 공간 맵의 벡터화 연산이며, 두 맵은 동일한 해상도(14×14)로 보간된다.

#### 3.3.2 AT와의 수식 수준 차별점

Attention Transfer(AT, Zagoruyko & Komodakis, 2017)의 손실 함수:

$$L_{AT} = \sum_{l} \left\| \frac{Q_S^l}{\|Q_S^l\|_2} - \frac{Q_T^l}{\|Q_T^l\|_2} \right\|_2$$

여기서 $Q^l = \sum_c |F^l_c|^p$ (activation norm의 공간적 합산)이다.

**AGSR과 AT의 핵심 차이**:
- AT: 중간층 activation의 **저수준 통계적 분포**를 전달
- AGSR: 세그멘테이션 마스크를 통해 투영된 **의미론적 객체 경계 일치도**를 전달

AGSR은 "어디를 보는가(공간적 위치)"가 아니라 "어떤 의미 구조를 보는가(객체 경계 일치)"를 정렬함으로써 형태 편향이라는 고수준 귀납 편향 자체를 이식한다.

### 3.4 전체 훈련 목적함수

$$\boxed{L_{total} = L_{CE} + \lambda_1 \cdot L_{AGSR} + \lambda_2 \cdot L_{KD}}$$

각 항의 정의:

**교차 엔트로피 손실**:
$$L_{CE} = -\sum_{c} y_c \log \hat{p}_c$$

**AGSR 정규화 손실** (방법 A 또는 B 선택):
$$L_{AGSR} \in \{L_{AGSR}^{IoU}, L_{AGSR}^{cos}\}$$

**지식 증류 손실** (소프트 레이블):
$$L_{KD} = \tau^2 \cdot \text{KL}\left(\sigma\left(\frac{z_S}{\tau}\right) \| \sigma\left(\frac{z_T}{\tau}\right)\right)$$

여기서 $\tau = 4.0$은 온도 파라미터, $z_S$와 $z_T$는 각각 학생(CNN)과 교사(ViT)의 로짓이다.

**하이퍼파라미터 설정**:
- $\lambda_1 \in \{0.1, 0.5, 1.0, 2.0\}$ (그리드 서치)
- $\lambda_2 \in \{0.5, 1.0, 2.0\}$ (그리드 서치)
- 기본값: $\lambda_1 = 1.0$, $\lambda_2 = 1.0$

### 3.5 효율적 오프라인 증류

#### 3.5.1 GSCS 사전 계산 및 캐싱

교사 ViT의 매 스텝 순전파 비용을 제거하기 위해 **훈련 전 1회** ImageNet 전체에 대한 GSCS(Global Shape Consistency Score)를 사전 계산하여 캐싱한다.

```python
# 의사 코드: GSCS 사전 계산
def precompute_gscs(dataset, teacher_vit, sam_tiny):
    gscs_cache = {}
    for img_id, image in tqdm(dataset):
        with torch.no_grad():
            # ViT 어텐션 맵 추출
            attn_map = teacher_vit.get_attention_rollout(image)
            # SAM-tiny 투영
            seg_mask = sam_tiny.segment(image, attn_map)
            # GSCS 저장
            gscs_cache[img_id] = seg_mask.cpu().numpy()
    
    # 디스크 캐싱 (HDF5 형식)
    save_to_hdf5(gscs_cache, 'gscs_cache.h5')
    return gscs_cache
```

**저장 용량 추정**: ImageNet 1.28M 이미지 × 14×14 마스크 × float16 ≈ **3.2GB** (실용적 범위)

#### 3.5.2 지연 업데이트 전략

동적 데이터 증강(RandAugment, MixUp, CutMix)으로 인해 캐싱된 GSCS와 증강된 이미지 사이의 불일치가 발생할 경우, **K=8 스텝마다 1회** 교사 순전파를 수행하는 지연 업데이트 전략을 병행한다.

$$\text{오버헤드 비율} = \frac{1}{K} \cdot \frac{C_{ViT}}{C_{CNN}} \approx \frac{1}{8} \times 0.72 \approx 9\%$$

여기서 $C_{ViT}/C_{CNN}$은 ViT-B/16과 ResNet-50의 상대적 순전파 비용 비율이다.

### 3.6 메커니즘 분석

#### 3.6.1 레이어별 형태 편향 분석

AGSR 적용 전후 각 레이어의 형태 편향 변화를 cue-conflict 자극 실험으로 측정한다. ResNet-50의 4개 스테이지(layer1~layer4)에서 Grad-CAM을 추출하고, 형태 선택 비율을 다음과 같이 정의한다:

$$\text{SBR}^l = \frac{\#\{\text{형태 일치 예측}\}}{\#\{\text{형태 일치 예측}\} + \#\{\text{텍스처 일치 예측}\}}$$

#### 3.6.2 이론적 정당화: 귀납 편향의 일반화 경계 관점

AGSR이 OOD 견고성을 향상시키는 메커니즘을 일반화 경계(generalization bound) 관점에서 설명한다. PAC-Bayes 프레임워크에서, 형태 편향 증가는 가설 공간을 텍스처 불변적 함수 클래스로 제한함으로써 OOD 도메인에서의 가설 복잡도를 감소시킨다:

$$\mathcal{R}_{OOD}(h) \leq \mathcal{R}_{ID}(h) + d_{\mathcal{H}}(\mathcal{D}_{ID}, \mathcal{D}_{OOD}) + \lambda$$

여기서 $d_{\mathcal{H}}$는 

## Appendix: Analysis Code

```python
"""
Attention-Guided Shape Regularization (AGSR) 실험 파이프라인
ViT vs CNN Image Classification Survey

연구 목표: ViT의 형태 편향을 CNN에 전이하여 OOD 견고성 향상
"""

# ============================================================
# 1. 필수 라이브러리 임포트
# ============================================================
import os
import sys
import time
import copy
import random
import warnings
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from scipy import stats
from scipy.stats import wilcoxon
from sklearn.metrics import confusion_matrix
from sklearn.manifold import TSNE

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, Subset
from torch.cuda.amp import autocast, GradScaler
import torchvision
import torchvision.transforms as transforms
import torchvision.models as models
from torchvision.datasets import ImageFolder

# timm: ViT 및 최신 CNN 아키텍처 지원
try:
    import timm
    from timm.models import create_model
    from timm.data import create_transform, resolve_data_config
    TIMM_AVAILABLE = True
except ImportError:
    TIMM_AVAILABLE = False
    warnings.warn("timm 미설치. pip install timm 실행 필요")

# Grad-CAM 구현을 위한 hooks
from torch.nn import Module

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 재현성을 위한 시드 고정
def set_seed(seed: int = 42):
    """모든 랜덤 시드 고정"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

set_seed(42)

# GPU 설정
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
NUM_GPUS = torch.cuda.device_count()
logger.info(f"사용 디바이스: {DEVICE}, GPU 수: {NUM_GPUS}")


# ============================================================
# 2. 실험 설정 데이터클래스
# ============================================================
@dataclass
class ExperimentConfig:
    """실험 전체 설정 관리"""
    # 경로 설정
    data_root: str = "/data/imagenet"
    imagenet_c_root: str = "/data/imagenet-c"
    imagenet_r_root: str = "/data/imagenet-r"
    imagenet_sketch_root: str = "/data/imagenet-sketch"
    imagenet_a_root: str = "/data/imagenet-a"
    objectnet_root: str = "/data/objectnet"
    texture_shape_root: str = "/data/texture-shape-cue-conflict"
    output_dir: str = "./agsr_results"
    
    # 모델 설정
    cnn_models: List[str] = field(default_factory=lambda: [
        'resnet50', 'resnet101', 'efficientnet_b4', 'convnext_base'
    ])
    vit_teacher: str = 'deit3_base_patch16_224'
    
    # 학습 하이퍼파라미터
    batch_size: int = 256  # 단일 GPU 기준 (실제: 1024 / 4 GPU)
    num_epochs: int = 300
    learning_rate: float = 1e-3
    weight_decay: float = 0.05
    warmup_epochs: int = 20
    
    # AGSR 하이퍼파라미터
    lambda_agsr: float = 0.1   # L_AGSR 가중치
    lambda_kd: float = 0.5     # L_KD 가중치
    temperature: float = 4.0   # 지식 증류 온도
    
    # 하이퍼파라미터 탐색 범위
    lambda_agsr_search: List[float] = field(default_factory=lambda: [0.01, 0.05, 0.1, 0.5, 1.0])
    lambda_kd_search: List[float] = field(default_factory=lambda: [0.1, 0.5, 1.0])
    
    # 평가 설정
    num_runs: int = 5          # 통계적 유의성을 위한 반복 실험 수
    imagenet_c_corruptions: List[str] = field(default_factory=lambda: [
        'gaussian_noise', 'shot_noise', 'impulse_noise',
        'defocus_blur', 'glass_blur', 'motion_blur', 'zoom_blur',
        'snow', 'frost', 'fog', 'brightness',
        'contrast', 'elastic_transform', 'pixelate', 'jpeg_compression'
    ])
    imagenet_c_severities: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    
    # 적대적 공격 설정
    fgsm_epsilons: List[float] = field(default_factory=lambda: [4/255, 8/255])
    pgd_epsilon: float = 4/255
    pgd_steps: int = 20
    pgd_step_size: float = 1/255
    
    # 이미지 설정
    img_size: int = 224
    num_classes: int = 1000
    num_workers: int = 8


config = ExperimentConfig()
os.makedirs(config.output_dir, exist_ok=True)


# ============================================================
# 3. 데이터 로드 및 전처리 템플릿
# ============================================================
class DatasetManager:
    """다중 데이터셋 로드 및 전처리 관리"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
        
        # 표준 ImageNet 전처리 (학습용)
        self.train_transform = transforms.Compose([
            transforms.RandomResizedCrop(config.img_size),
            transforms.RandomHorizontalFlip(),
            transforms.RandAugment(num_ops=2, magnitude=9),  # RandAugment
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225]),
        ])
        
        # 평가용 전처리
        self.val_transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(config.img_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225]),
        ])
        
        # MixUp/CutMix 설정 (학습 시 적용)
        self.mixup_alpha = 0.8
        self.cutmix_alpha = 1.0
    
    def get_imagenet_loaders(self) -> Tuple[DataLoader, DataLoader]:
        """ImageNet-1K 학습/검증 데이터로더 반환"""
        train_dataset = ImageFolder(
            root=os.path.join(self.config.data_root, 'train'),
            transform=self.train_transform
        )
        val_dataset = ImageFolder(
            root=os.path.join(self.config.data_root, 'val'),
            transform=self.val_transform
        )
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=self.config.num_workers,
            pin_memory=True,
            drop_last=True
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.batch_size * 2,
            shuffle=False,
            num_workers=self.config.num_workers,
            pin_memory=True
        )
        
        logger.info(f"ImageNet-1K: 학습 {len(train_dataset):,}장, 검증 {len(val_dataset):,}장")
        return train_loader, val_loader
    
    def get_imagenet100_loader(self) -> Tuple[DataLoader, DataLoader]:
        """ImageNet-100 서브셋 로더 (하이퍼파라미터 탐색용)"""
        # ImageNet-100 클래스 인덱스 (예시: 처음 100개 클래스)
        full_train = ImageFolder(
            root=os.path.join(self.config.data_root, 'train'),
            transform=self.train_transform
        )
        
        # 100개 클래스만 선택
        class_to_idx = full_train.class_to_idx
        selected_classes = list(class_to_idx.values())[:100]
        
        # 선택된 클래스의 샘플만 필터링
        indices = [i for i, (_, label) in enumerate(full_train.samples)
                  if label in selected_classes]
        
        subset = Subset(full_train, indices)
        loader = DataLoader(subset, batch_size=self.config.batch_size,
                           shuffle=True, num_workers=self.config.num_workers)
        
        logger.info(f"ImageNet-100: {len(subset):,}장 로드")
        return loader
    
    def get_imagenet_c_loader(self, corruption: str, severity: int) -> DataLoader:
        """ImageNet-C 특정 corruption/severity 데이터로더"""
        dataset_path = os.path.join(
            self.config.imagenet_c_root, corruption, str(severity)
        )
        
        if not os.path.exists(dataset_path):
            logger.warning(f"ImageNet-C 경로 없음: {dataset_path}")
            return self._create_dummy_loader()
        
        dataset = ImageFolder(root=dataset_path, transform=self.val_transform)
        loader = DataLoader(
            dataset,
            batch_size=self.config.batch_size * 2,
            shuffle=False,
            num_workers=self.config.num_workers,
            pin_memory=True
        )
        return loader
    
    def get_ood_loaders(self) -> Dict[str, DataLoader]:
        """OOD 평가 데이터셋 로더 딕셔너리 반환"""
        ood_loaders = {}
        
        ood_datasets = {
            'imagenet_r': self.config.imagenet_r_root,
            'imagenet_sketch': self.config.imagenet_sketch_root,
            'imagenet_a': self.config.imagenet_a_root,
            'objectnet': self.config.objectnet_root,
        }
        
        for name, path in ood_datasets.items():
            if os.path.exists(path):
                dataset = ImageFolder(root=path, transform=self.val_transform)
                ood_loaders[name] = DataLoader(
                    dataset,
                    batch_size=self.config.batch_size * 2,
                    shuffle=False,
                    num_workers=self.config.num_workers,
                    pin_memory=True
                )
                logger.info(f"{name}: {len(dataset):,}장 로드")
            else:
                logger.warning(f"{name} 경로 없음: {path}")
                ood_loaders[name] = self._create_dummy_loader()
        
        return ood_loaders
    
    def _create_dummy_loader(self, num_samples: int = 1000) -> DataLoader:
        """경로가 없을 때 더미 데이터로더 생성 (테스트용)"""
        class DummyDataset(Dataset):
            def __init__(self, n, num_classes=1000, img_size=224):
                self.n = n
                self.num_classes = num_classes
                self.img_size = img_size
            
            def __len__(self):
                return self.n
            
            def __getitem__(self, idx):
                img = torch.randn(3, self.img_size, self.img_size)
                label = torch.randint(0, self.num_classes, (1,)).item()
                return img, label
        
        dummy = DummyDataset(num_samples)
        return DataLoader(dummy, batch_size=64, shuffle=False)
    
    def apply_mixup(self, x: torch.Tensor, y: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
        """MixUp 데이터 증강 적용"""
        lam = np.random.beta(self.mixup_alpha, self.mixup_alpha)
        batch_size = x.size(0)
        index = torch.randperm(batch_size).to(x.device)
        
        mixed_x = lam * x + (1 - lam) * x[index]
        y_a, y_b = y, y[index]
        return mixed_x, y_a, y_b, lam
    
    def apply_cutmix(self, x: torch.Tensor, y: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
        """CutMix 데이터 증강 적용"""
        lam = np.random.beta(self.cutmix_alpha, self.cutmix_alpha)
        batch_size, _, H, W = x.size()
        index = torch.randperm(batch_size).to(x.device)
        
        # 랜덤 박스 생성
        cut_ratio = np.sqrt(1 - lam)
        cut_h = int(H * cut_ratio)
        cut_w = int(W * cut_ratio)
        
        cx = np.random.randint(W)
        cy = np.random.randint(H)
        
        x1 = np.clip(cx - cut_w // 2, 0, W)
        y1 = np.clip(cy - cut_h // 2, 0, H)
        x2 = np.clip(cx + cut_w // 2, 0, W)
        y2 = np.clip(cy + cut_h // 2, 0, H)
        
        mixed_x = x.clone()
        mixed_x[:, :, y1:y2, x1:x2] = x[index, :, y1:y2, x1:x2]
        
        # 실제 lam 재계산
        lam = 1 - (y2 - y1) * (x2 - x1) / (H * W)
        y_a, y_b = y, y[index]
        return mixed_x, y_a, y_b, l
```