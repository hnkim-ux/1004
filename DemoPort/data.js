// 사이트 콘텐츠. 코드 수정 없이 이 파일만 고쳐서 내용을 갱신한다.
// TODO 표시가 있는 값은 실제 정보로 바꿔야 한다.
window.PROFILE = {
  name: "hnkim", // TODO: 표시할 이름 (국문/영문)
  role: "QA SW Engineer",
  tagline: "전장 검증 전문 QA SW 엔지니어",
  intro:
    "차량 전장 시스템이 요구사항대로, 안전하게 동작하는지 증명하는 일을 합니다. " +
    "요구사항 분석부터 테스트 설계, 자동화, 결함 추적까지 검증 전 과정을 책임집니다.",
  email: "hnkim@infiniq.co.kr",

  about: [
    "QA SW 엔지니어로서 소프트웨어 품질 보증을 주 업무로 하고, 그중에서도 전장(차량 전자/전기) 시스템 검증을 주력으로 하고 있습니다.",
    "좋은 검증은 결함을 찾는 것에서 끝나지 않고, 요구사항과 테스트 사이의 추적성을 남겨 누구나 품질을 신뢰할 수 있게 만드는 것이라고 생각합니다.",
  ],

  highlights: [
    { value: "QA SW", label: "주 업무 분야" },
    { value: "전장 검증", label: "주력 분야" },
    { value: "E2E", label: "요구사항 → 테스트 → 결함 추적" },
  ],

  // TODO: 실제 경험에 맞게 항목을 고르거나 수정
  expertise: [
    {
      title: "검증 레벨",
      icon: "layers",
      items: ["SW 단위 / 통합 테스트", "HILS (Hardware-in-the-Loop)", "SILS / MIL", "실차 검증"],
    },
    {
      title: "차량 통신",
      icon: "signal",
      items: ["CAN / CAN-FD", "LIN", "Automotive Ethernet", "UDS 진단"],
    },
    {
      title: "표준 · 프로세스",
      icon: "shield",
      items: ["ASPICE", "ISO 26262 (기능안전)", "ISO 21434 (사이버보안)"],
    },
    {
      title: "검증 산출물",
      icon: "doc",
      items: ["테스트 명세서", "요구사항 추적성 매트릭스", "결함 리포트 · 분석"],
    },
  ],

  skills: [
    { group: "검증 도구", items: ["Vector CANoe", "CANalyzer", "dSPACE", "CAPL"] },
    { group: "자동화 · 언어", items: ["Python", "pytest", "CAPL Script"] },
    { group: "협업 · 관리", items: ["JIRA", "Git", "Confluence"] },
  ],

  // TODO: 공개 가능한 실제 프로젝트로 교체 (아래는 형식 예시)
  projects: [
    {
      title: "예시) 바디 제어기 기능 검증",
      period: "20XX.XX – 20XX.XX",
      system: "BCM",
      role: "테스트 설계 · HILS 자동화",
      tools: ["CANoe", "CAPL", "Python"],
      metrics: [
        { value: "000+", label: "테스트 케이스" },
        { value: "00%", label: "자동화율" },
      ],
    },
    {
      title: "예시) 클러스터 통신 진단 검증",
      period: "20XX.XX – 20XX.XX",
      system: "Cluster",
      role: "UDS 진단 시험 · 결함 분석",
      tools: ["CANalyzer", "UDS"],
      metrics: [
        { value: "00", label: "결함 검출" },
        { value: "00%", label: "검증 기간 단축" },
      ],
    },
  ],

  // TODO: 실제 경력으로 교체
  experience: [
    { period: "20XX – 현재", org: "소속 회사", role: "QA SW Engineer · 전장 검증" },
  ],
};
