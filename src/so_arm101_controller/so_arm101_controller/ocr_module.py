import os
import tempfile
import logging
from typing import List, Dict, Optional, Tuple
import cv2
import numpy as np

"""
고도화된 OCR 모듈 (PaddleOCR 기반)
- 딥러닝 모델 친화적인 컬러 유지 전처리 (2배 확대 및 가벼운 선명화) 적용
- 기하학적 픽셀 거리 계산을 통한 띄어쓰기 강제 복원 파이프라인 포함
"""

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class OCRModule:
    def __init__(self, lang: str = "korean", ocr_version: str = "PP-OCRv3"):
        self.lang = lang
        self.ocr_version = ocr_version
        self._engine = None

    def _init_engine(self):
        if self._engine is not None:
            return
        try:
            from paddleocr import PaddleOCR
        except Exception as e:
            logger.error("PaddleOCR 임포트 실패: %s", e)
            raise

        try:
            # 💡 딥러닝 최적화 파라미터 적용 (정확도 극대화)
            self._engine = PaddleOCR(
                lang=self.lang,
                ocr_version=self.ocr_version,
                use_angle_cls=True,         # 비스듬히 찍힌 글자 자동 회전 보정
                det_db_thresh=0.3,          # 희미한 글자도 잘 잡도록 임계값 하향
                det_db_unclip_ratio=1.6,    # 글자 박스를 여유있게 잡아 잘림 방지
                det_db_box_thresh=0.5
            )
            logger.info("PaddleOCR 엔진 초기화 성공")
        except Exception as e:
            logger.error("엔진 생성 실패: %s", e)
            raise

    def _call_engine_with_file(self, path: str):
        self._init_engine()
        engine = self._engine
        try:
            if hasattr(engine, "ocr"):
                return engine.ocr(path, cls=True)
        except Exception:
            pass
        try:
            if hasattr(engine, "predict"):
                return engine.predict(path)
        except Exception:
            pass
        return engine(path)

    def _parse_results_with_spacing(self, results) -> List[Dict[str, str]]:
        text_list: List[Dict[str, str]] = []
        if not results:
            return text_list

        # 최신 PaddleOCR dict 포맷 대응 (이중 리스트 포장 해제)
        if isinstance(results, list) and len(results) > 0 and isinstance(results[0], dict):
            results = results[0]
        
        if isinstance(results, dict) and 'rec_texts' in results:
            try:
                lines = []
                rec_polys = results.get('rec_polys', [])
                rec_texts = results.get('rec_texts', [])
                rec_scores = results.get('rec_scores', [])
                for i in range(len(rec_texts)):
                    box = rec_polys[i].tolist() if hasattr(rec_polys[i], 'tolist') else rec_polys[i]
                    txt = rec_texts[i]
                    score = rec_scores[i] if i < len(rec_scores) else 0.99
                    lines.append([box, (txt, score)])
                results = [lines]
            except Exception as e:
                logger.error(f"데이터 추출 중 에러: {e}")

        if not results or not isinstance(results, list) or not results[0]:
            return text_list

        try:
            lines = results[0]
            lines = sorted(lines, key=lambda x: (x[0][0][1] // 15, x[0][0][0]))

            rewritten_text = ""
            prev_box_end_x = None
            prev_box_y = None

            for item in lines:
                box = item[0]
                txt, score = item[1]
                curr_start_x = box[0][0]
                curr_end_x = box[1][0]
                curr_y = box[0][1]
                char_height = abs(box[3][1] - box[0][1])
                space_threshold = char_height * 0.35

                if prev_box_end_x is not None and abs(curr_y - prev_box_y) < char_height:
                    distance = curr_start_x - prev_box_end_x
                    if distance > space_threshold:
                        rewritten_text += " " + str(txt)
                    else:
                        rewritten_text += str(txt)
                else:
                    if rewritten_text:
                        text_list.append({"text": rewritten_text.strip(), "score": f"{float(score):.2f}"})
                    rewritten_text = str(txt)

                prev_box_end_x = curr_end_x
                prev_box_y = curr_y

            if rewritten_text:
                text_list.append({"text": rewritten_text.strip(), "score": "0.90"})

            return text_list
        except Exception as e:
            logger.debug("정밀 띄어쓰기 파싱 실패, fallback 전환: %s", e)
            return self._parse_results_fallback(results)

    def _parse_results_fallback(self, results) -> List[Dict[str, str]]:
        text_list: List[Dict[str, str]] = []
        try:
            if isinstance(results, list) and len(results) > 0 and isinstance(results[0], dict):
                results = results[0]
            if isinstance(results, dict) and 'rec_texts' in results:
                rec_texts = results['rec_texts']
                for txt in rec_texts:
                    text_list.append({"text": str(txt), "score": "0.99"})
                return text_list
            for res in results:
                if not res:
                    continue
                for item in res:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        content = item[1]
                        if isinstance(content, (list, tuple)) and len(content) >= 2:
                            text_list.append({"text": str(content[0]), "score": f"{float(content[1]):.2f}"})
        except Exception:
            pass
        return text_list

    def ocr_from_image(self, frame: np.ndarray, bbox: Optional[Tuple[int, int, int, int]] = None, pad: int = 8) -> List[Dict[str, str]]:
        if frame is None:
            return []

        roi = frame
        if bbox is not None:
            x1, y1, x2, y2 = bbox
            h, w = frame.shape[:2]
            # 💡 크롭 시 패딩을 타이트하게(5) 주어 불필요한 배경 노이즈를 1차적으로 날려버립니다.
            pad = max(pad, 5)
            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(w - 1, x2 + pad)
            y2 = min(h - 1, y2 + pad)
            roi = frame[y1:y2, x1:x2]

        try:
            # 💡 딥러닝 친화적 자연스러운 전처리 + 흑백(Grayscale) 변환 적용
            
            # 1. 2배 확대 (해상도를 높여 작은 글자 인식률 향상)
            resized_roi = cv2.resize(roi, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            
            # 2. 흑백(Grayscale) 변환 적용 (컬러 노이즈 제거)
            gray_roi = cv2.cvtColor(resized_roi, cv2.COLOR_BGR2GRAY)
            
            # 3. 아주 가벼운 언샤프 마스킹 (흑백 상태에서 경계선만 살짝 뚜렷하게)
            blurred = cv2.GaussianBlur(gray_roi, (0, 0), 2.0)
            sharpened_roi = cv2.addWeighted(gray_roi, 1.5, blurred, -0.5, 0)
            
            # 4. PaddleOCR 엔진 호환성을 위해 3채널(BGR) 구조로 복원 (시각적으로는 흑백 유지)
            processed_roi = cv2.cvtColor(sharpened_roi, cv2.COLOR_GRAY2BGR)
            
        except Exception as e:
            logger.error("전처리 오류: %s", e)
            processed_roi = roi

        try:
            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(tmp_fd) 
            success = cv2.imwrite(tmp_path, processed_roi)
            if not success:
                return []
            results = self._call_engine_with_file(tmp_path)
            parsed = self._parse_results_with_spacing(results)
            return parsed
        finally:
            try:
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass