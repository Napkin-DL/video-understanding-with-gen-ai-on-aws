# AWS의 Generative AI를 활용한 비디오 이해 워크숍


개발자와 솔루션 빌더를 대상으로 하는 이 실습 워크숍은 [Amazon Bedrock](https://aws.amazon.com/bedrock/)을 통해 AWS AI Services와 foundation models (FMs)를 활용하여 비디오 이해 사용 사례를 구현하는 방법을 소개합니다. 이 코드는 자율 학습 또는 강사 주도 워크숍과 함께 제공됩니다 - [AWS의 Generative AI를 활용한 비디오 이해](https://catalog.us-east-1.prod.workshops.aws/workshops/7db2455e-0fa6-4f6d-9973-84daccd6421f)

**위 링크에 나열된 prerequisites를 따르거나 AWS 워크숍 강사에게 시작 방법을 문의하세요.**

이 일련의 실습에서는 Generative AI를 활용한 비디오 이해와 관련하여 고객들에게서 가장 일반적으로 보이는 사용 패턴을 탐구할 것입니다. 비디오를 작은 클립으로 세그먼트화하고 다양한 세그먼테이션 수준에서 비디오에 대한 풍부한 맥락적 메타데이터를 생성하는 기술을 보여드릴 것입니다.

실습 내용:

- **01 - Video Time Segmentation** $$예상 소요 시간 - 45분$$
- **02 - Ad Breaks and Contextual Advertising** $$예상 소요 시간 - 30분$$
- **02 - Video Summarization** $$예상 소요 시간 - 30분$$
- **03 - Multi-modal Semantic Search** $$예상 소요 시간 - 30분$$

## 시작하기

이 워크숍은 선택한 환경에서 실행할 수 있는 **Python notebooks** 시리즈로 제공됩니다:

- 풍부한 AI/ML 기능을 갖춘 완전 관리형 환경을 위해서는 [SageMaker Studio](https://aws.amazon.com/sagemaker/studio/)를 추천합니다. 빠르게 시작하려면 [domain quick setup 지침](https://docs.aws.amazon.com/sagemaker/latest/dg/onboard-quick-start.html)을 참조할 수 있습니다.
- 완전 관리형이지만 더 기본적인 경험을 원한다면 대신 [SageMaker Notebook Instance 생성](https://docs.aws.amazon.com/sagemaker/latest/dg/howitworks-create-ws.html)을 선택할 수 있습니다.
- 기존(로컬 또는 기타) 노트북 환경을 사용하고 싶다면 [AWS 호출을 위한 자격 증명](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)이 있는지 확인하세요.

### 노트북 복제 및 사용

> ℹ️ **참고:** SageMaker Studio에서는 _File > New > Terminal_을 클릭하여 "System Terminal"을 열어 이러한 명령을 실행할 수 있습니다.

노트북 환경 설정이 완료되면 이 워크숍 리포지토리를 복제하세요.

```sh
sudo yum install -y unzip
git clone https://github.com/aws-samples/video-understanding-with-generative-ai-on-aws.git
cd video-understanding-with-generative-ai-on-aws
```

```sh
sudo yum install -y unzip
git clone https://github.com/aws-samples/video-understanding-with-generative-ai-on-aws.git
cd video-understanding-with-generative-ai-on-aws
```

You're now ready to explore the lab notebooks! Start with [00_prerequisites.ipynb](00_prerequisites.ipynb).

## Security

샘플 코드, 소프트웨어 라이브러리, 명령줄 도구, 개념 증명, 템플릿 또는 기타 관련 기술(당사 직원이 제공하는 모든 것 포함)은 AWS 고객 계약 또는 귀하와 AWS 간의 관련 서면 계약(해당되는 것)에 따라 AWS 콘텐츠로 제공됩니다. 이 AWS 콘텐츠를 프로덕션 계정이나 프로덕션 또는 기타 중요한 데이터에 사용해서는 안 됩니다. 귀하는 특정 품질 관리 관행 및 표준에 따라 프로덕션 등급 사용에 적합하도록 샘플 코드와 같은 AWS 콘텐츠를 테스트, 보안 및 최적화할 책임이 있습니다. AWS 콘텐츠를 배포하면 Amazon EC2 인스턴스 실행 또는 Amazon S3 스토리지 사용과 같은 AWS 과금 가능 리소스를 생성하거나 사용하는 데 AWS 요금이 발생할 수 있습니다.
## License

See [LICENSE](LICENSE).

## Notices

See [NOTICES](NOTICE).