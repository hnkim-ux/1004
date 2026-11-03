import type { Comment, Database, Post } from "@/lib/db";

const SEED_TITLES = [
  "게시판에 오신 것을 환영합니다",
  "CAN 통신 로그 분석 팁 공유",
  "HIL 테스트 벤치 구성 질문드립니다",
  "ISO 26262 기능 안전 스터디 모집",
  "AUTOSAR 기본 개념 정리",
  "UDS 진단 서비스 0x22 / 0x2E 차이",
  "테스트 케이스 작성 템플릿 공유",
  "CANoe CAPL 스크립트 디버깅 방법",
  "결함 리포트 잘 쓰는 법",
  "회귀 테스트 자동화 도입 후기",
  "LIN 버스 슬립/웨이크업 시나리오",
  "Next.js App Router 써 본 소감",
  "요구사항 추적성(Traceability) 관리 도구 추천",
  "ECU 플래싱 실패 원인 정리",
  "주간 QA 회의록 (1주차)",
  "주간 QA 회의록 (2주차)",
  "다크 모드 지원 테스트",
  "반응형 레이아웃 확인용 긴 제목의 게시글입니다 — 모바일에서 줄바꿈이 잘 되는지 확인해 보세요",
  "Ethernet(DoIP) 진단 연결 체크리스트",
  "테스트 커버리지 지표, 무엇을 봐야 할까",
  "MISRA C 규칙 위반 자주 나오는 항목",
  "탐색적 테스트 세션 진행 방법",
  "게시판 사용 가이드",
];

const AUTHORS = ["관리자", "김테스터", "이엔지니어", "박검증", "최QA"];

export function createSeed(): Database {
  const base = Date.UTC(2026, 9, 1, 0, 0, 0);
  const posts: Post[] = SEED_TITLES.map((title, index) => {
    const createdAt = new Date(base + index * 26 * 60 * 60 * 1000).toISOString();
    return {
      id: index + 1,
      title,
      content: `${title}\n\n샘플 게시글 본문입니다. 자유롭게 수정하거나 삭제해 보세요.\n줄바꿈도 그대로 표시됩니다.`,
      author: AUTHORS[index % AUTHORS.length],
      createdAt,
      updatedAt: createdAt,
    };
  });

  const comments: Comment[] = [
    { postId: 1, author: "김테스터", content: "반갑습니다!" },
    { postId: 1, author: "박검증", content: "잘 쓰겠습니다." },
    { postId: 2, author: "이엔지니어", content: "필터 설정 팁도 부탁드려요." },
    { postId: SEED_TITLES.length, author: "최QA", content: "가이드 감사합니다." },
  ].map((comment, index) => ({
    id: index + 1,
    ...comment,
    createdAt: new Date(base + (index + 1) * 60 * 60 * 1000).toISOString(),
  }));

  return {
    nextPostId: posts.length + 1,
    nextCommentId: comments.length + 1,
    posts,
    comments,
  };
}
