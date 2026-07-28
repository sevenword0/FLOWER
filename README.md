# FLOWER — WebGPU 절차적 꽃 개화 시뮬레이터

WebGPU로 다양한 꽃이 실시간으로 피어나는 모습을 절차적으로 생성·변형·관찰하는 **단일 HTML 앱**입니다. 의존성 0, 더블클릭으로도 실행됩니다.

## 라이브 데모

GitHub Pages 배포가 활성화되면 다음 주소에서 바로 볼 수 있습니다:

**https://sevenword0.github.io/FLOWER/**

> 요구 사항: WebGPU 지원 브라우저 (Chrome/Edge 113+, Safari 18+) · HTTPS

## 어류 절차 생태계 관측 콘솔

같은 저장소에 근거 추적형 **어류 절차 생성·자율행동 생태 시뮬레이터**가 함께 들어 있습니다.

**https://sevenword0.github.io/FLOWER/fish/**

- 의존성 0의 단일 HTML (WebGL2). 프리셋 → 절차적 메시 → 유영 진동자 → 에토그램 행동 → 생태 상호작용을 브라우저에서 실시간 구동합니다.
- 무리 최근접거리(NND)를 관측 문헌 범위(0.3–1.2 BL)와 실시간 대조하는 검증 계기를 내장했습니다.
- 대상 생물군 선택기로 "한 단어 교체" 이식성(Gate G9)을 직접 확인할 수 있습니다.
- 파이프라인 본체(스키마·증거 원장·프리셋 컴파일러·테스트)는 `project/` 에 있습니다. `project/README.md` 참고.

## 실행 방법

- **로컬**: `index.html` 을 WebGPU 지원 브라우저로 엽니다.
- **웹**: 위 라이브 데모 링크.

## 주요 기능

- 2패스 디퍼드 렌더링 (G-buffer MRT + composite)
- 화면공간 AO + SSGI(1바운스) + 소프트 섀도우, ACES 톤매핑
- 꽃잎 인스턴싱 기반 절차적 꽃 생성 (꽃잎·관상화·잎·수술·암술)
- 실시간 개화 애니메이션 및 형태/조명/장면 컨트롤 (4탭 UI)
- 8종 프리셋 (장미·데이지·해바라기·튤립·백합·연꽃·벚꽃·달리아)

## 배포 (GitHub Pages)

`.github/workflows/pages.yml` 워크플로가 `main` 브랜치 푸시 시 리포 루트(`index.html`)를 Pages에 빌드·배포합니다. 수동 실행은 Actions 탭의 *Deploy to GitHub Pages* → *Run workflow* 로도 가능합니다.

> **최초 1회 설정 필요**: GitHub 보안 정책상 워크플로의 자동 토큰은 Pages를 처음으로 켤 수 없습니다.
> 리포 **Settings → Pages → Build and deployment → Source** 를 **`GitHub Actions`** 로 한 번 설정한 뒤
> 워크플로를 다시 실행하면 배포가 완료됩니다. 이후부터는 `main` 푸시마다 자동 배포됩니다.
