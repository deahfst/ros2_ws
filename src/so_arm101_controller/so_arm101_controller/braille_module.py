import os
from jamo import hangul_to_jamo, jamo_to_hcj

# --- 국립국어원 규정 반영 점자 핀 매핑 딕셔너리 ---
BRAILLE_MAP = {
    # 특수 전표
    'DOUBLE_CONSONANT_PREFIX': [0, 0, 0, 0, 0, 1], # 된소리표 (초성 쌍자음 앞)
    'NUMBER_PREFIX': [0, 0, 1, 1, 1, 1],            # 수표 (숫자 시작 앞)

    # 초성 (첫소리 기본 자음)
    'ㄱ': [0, 0, 0, 1, 0, 0], 'ㄴ': [1, 0, 0, 1, 0, 0], 'ㄷ': [0, 1, 0, 1, 0, 0],
    'ㄹ': [0, 0, 0, 0, 1, 0], 'ㅁ': [1, 0, 0, 0, 1, 0], 'ㅂ': [0, 0, 0, 1, 1, 0],
    'ㅅ': [0, 0, 0, 0, 0, 1], 'ㅇ': [1, 1, 1, 1, 1, 1],
    'ㅈ': [0, 1, 0, 0, 0, 1], 'ㅊ': [0, 0, 0, 1, 0, 1], 'ㅋ': [1, 1, 0, 1, 0, 0],
    'ㅌ': [1, 1, 0, 0, 1, 0], 'ㅍ': [1, 0, 0, 1, 1, 0], 'ㅎ': [0, 1, 0, 1, 1, 0],
    'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ',

    # 중성 (모음)
    'ㅏ': [1, 1, 0, 0, 0, 0], 'ㅑ': [0, 0, 1, 1, 1, 0], 'ㅓ': [0, 1, 1, 1, 0, 0],
    'ㅕ': [1, 0, 0, 0, 1, 1], 'ㅗ': [1, 0, 1, 0, 0, 0], 'ㅛ': [0, 0, 1, 1, 0, 1],
    'ㅜ': [1, 0, 1, 1, 0, 0], 'ㅠ': [1, 0, 0, 1, 0, 1], 'ㅡ': [0, 1, 0, 1, 0, 1],
    'ㅣ': [1, 0, 1, 0, 1, 0], 'ㅐ': [1, 1, 1, 0, 1, 0], 'ㅔ': [1, 0, 1, 1, 1, 0],
    'ㅒ': [0, 0, 1, 1, 1, 0], 'ㅖ': [0, 0, 1, 1, 0, 0], 'ㅘ': [1, 1, 1, 0, 0, 0], 
    'ㅝ': [1, 0, 1, 1, 1, 1], 'ㅚ': [1, 0, 1, 1, 1, 0], 'ㅟ': [1, 0, 1, 1, 1, 1], 
    'ㅢ': [0, 1, 1, 1, 0, 1],
    
    # 종성 (받침)
    'ㄱ_종': [1, 0, 0, 0, 0, 0], 'ㄴ_종': [0, 1, 0, 0, 1, 0], 'ㄷ_종': [0, 0, 1, 1, 0, 0],
    'ㄹ_종': [0, 1, 0, 0, 0, 0], 'ㅁ_종': [0, 1, 0, 0, 0, 1], 'ㅂ_종': [1, 1, 0, 0, 0, 0],
    'ㅅ_종': [0, 0, 1, 0, 0, 0], 'ㅇ_종': [0, 1, 1, 0, 1, 1], 'ㅈ_종': [1, 0, 1, 0, 0, 0],
    'ㅊ_종': [0, 1, 1, 0, 0, 0], 'ㅋ_종': [1, 1, 0, 1, 0, 0], 'ㅌ_종': [1, 1, 0, 0, 1, 0],
    'ㅍ_종': [1, 0, 0, 1, 1, 0], 'ㅎ_종': [0, 1, 0, 1, 1, 0],
    'ㄲ_종': [1, 0, 0, 1, 0, 0], 'ㄳ_종': [1, 0, 1, 0, 0, 0], 'ㄵ_종': [0, 1, 1, 0, 0, 0],
    'ㄶ_종': [0, 1, 0, 1, 1, 0], 'ㄺ_종': [0, 1, 0, 1, 0, 0], 'ㄻ_종': [0, 1, 0, 0, 1, 1],
    'ㄼ_종': [0, 1, 0, 1, 1, 0], 'ㄽ_종': [0, 1, 1, 0, 0, 0], 'ㄾ_종': [0, 1, 1, 0, 1, 0],
    'ㄿ_종': [0, 1, 0, 1, 1, 0], 'ㅀ_종': [0, 1, 0, 1, 1, 1], 'ㅄ_종': [1, 1, 1, 0, 0, 0],
    'ㅆ_종': [0, 0, 1, 0, 1, 0],

    # 숫자 (0 ~ 9)
    '1': [1, 0, 0, 0, 0, 0], '2': [1, 1, 0, 0, 0, 0], '3': [1, 0, 0, 1, 0, 0],
    '4': [1, 0, 0, 1, 1, 0], '5': [1, 0, 0, 0, 1, 0], '6': [1, 1, 0, 1, 0, 0],
    '7': [1, 1, 0, 1, 1, 0], '8': [1, 1, 0, 0, 1, 0], '9': [0, 1, 0, 1, 0, 0],
    '0': [0, 1, 0, 1, 1, 0],

    # --- 국립국어원 표준 문장 부호 및 기호 매핑 ---
    ' ': [0, 0, 0, 0, 0, 0],      # 빈칸 / 공백
    '.': [0, 1, 0, 0, 1, 1],      # 마침표 / 온점
    ',': [0, 1, 0, 0, 0, 0],      # 쉼표 / 반점
    '?': [0, 1, 1, 0, 0, 1],      # 물음표
    ';': [0, 1, 1, 0, 1, 0],      # 세미콜론
    '/': [0, 0, 1, 1, 0, 0],      # 빗금 (슬래시)
    '%': [0, 0, 1, 1, 0, 1],      # 퍼센트
    '+': [0, 0, 1, 1, 1, 0],      # 더하기
    '-': [0, 0, 1, 0, 0, 1],      # 붙임표 / 마이너스 / 하이픈
    '*': [0, 0, 1, 0, 1, 1],      # 별표 (통상 기호)
    '=': [0, 0, 1, 1, 1, 1],      # 같다 (등호)

    '!': ([0, 1, 1, 0, 1, 0], [0, 0, 0, 0, 0, 1]),       # 느낌표
    ':': ([0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1]),       # 쌍점 (콜론)
    '(': ([0, 1, 1, 1, 0, 0], [0, 1, 0, 0, 0, 0]),       # 여는 소괄호
    ')': ([0, 1, 0, 0, 0, 0], [0, 0, 1, 1, 1, 0]),       # 닫는 소괄호
    '{': ([0, 1, 1, 1, 0, 0], [1, 0, 1, 0, 0, 0]),       # 여는 중괄호
    '}': ([1, 0, 1, 0, 0, 0], [0, 0, 1, 1, 1, 0]),       # 닫는 중괄호
    '[': ([0, 1, 1, 1, 0, 0], [0, 1, 1, 0, 1, 0]),       # 여는 대괄호
    ']': ([0, 1, 1, 0, 1, 0], [0, 0, 1, 1, 1, 0]),       # 닫는 대괄호
    '~': ([0, 0, 1, 0, 0, 1], [0, 0, 1, 0, 0, 1]),       # 물결표
    
    'OPEN_QUOTE_DOUBLE': [0, 1, 1, 0, 1, 1],             # 여는 큰따옴표 (")
    'CLOSE_QUOTE_DOUBLE': [0, 1, 1, 0, 1, 1],            # 닫는 큰따옴표 (")
    'OPEN_QUOTE_SINGLE': ([0, 0, 1, 0, 1, 1], [0, 1, 1, 0, 1, 1]), # 여는 작은따옴표 (')
    'CLOSE_QUOTE_SINGLE': ([0, 1, 1, 0, 1, 1], [0, 0, 1, 1, 0, 0]) # 닫는 작은따옴표 (')
}

def text_to_braille_pins(text):
    """텍스트 문자열을 입력받아 각 글자별 점자 핀 매핑 딕셔너리의 리스트를 반환합니다."""
    braille_sequence = []
    in_number = False  
    is_dquote_open = False 
    is_squote_open = False 
    
    # 원본 코드 버그 수정: 초성 된소리 매핑 시 BRAILLE_MAP[cho]가 문자열('ㄱ')이므로
    # 재참조할 수 있도록 임시 핸들러를 구성하거나 직접 매핑 문자열을 타겟팅해야 합니다.
    # 안전한 처리를 위해 딕셔너리 하드코딩 오류를 유연하게 처리하도록 로직을 수정했습니다.
    DOUBLE_CONSONANT_MAP = {'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ'}
    
    for char in text:
        # 1. 공백 처리
        if char in [' ', '\n', '\r']:
            in_number = False
            braille_sequence.append({'char': '공백', 'pins': BRAILLE_MAP[' ']})
            continue
            
        # 2. 숫자 처리
        if char.isdigit():
            if not in_number:
                braille_sequence.append({'char': '수표', 'pins': BRAILLE_MAP['NUMBER_PREFIX']})
                in_number = True
            braille_sequence.append({'char': f'숫자 {char}', 'pins': BRAILLE_MAP[char]})
            continue
        else:
            if char not in ['%', '+', '-', '=', '/']: 
                in_number = False

        # 3. 한글 처리
        if '가' <= char <= '힣':
            jamo_str = list(jamo_to_hcj(hangul_to_jamo(char)))
            cho = jamo_str[0]
            jung = jamo_str[1]
            jong = jamo_str[2] if len(jamo_str) == 3 else None
            
            if cho != 'ㅇ':
                if cho in DOUBLE_CONSONANT_MAP:
                    braille_sequence.append({'char': f'{cho}(초-된소리표)', 'pins': BRAILLE_MAP['DOUBLE_CONSONANT_PREFIX']})
                    base_cho = DOUBLE_CONSONANT_MAP[cho]
                    braille_sequence.append({'char': f'{base_cho}(초-기본)', 'pins': BRAILLE_MAP[base_cho]})
                elif cho in BRAILLE_MAP:
                    braille_sequence.append({'char': f'{cho}(초)', 'pins': BRAILLE_MAP[cho]})
            
            if jung in BRAILLE_MAP:
                braille_sequence.append({'char': f'{jung}(중)', 'pins': BRAILLE_MAP[jung]})
                
            if jong:
                jong_key = f'{jong}_종'
                if jong_key in BRAILLE_MAP:
                    braille_sequence.append({'char': f'{jong}(종)', 'pins': BRAILLE_MAP[jong_key]})
                    
        # 4. 큰따옴표 (") 토글 처리
        elif char in ['"', '“', '”']:
            if not is_dquote_open:
                braille_sequence.append({'char': '여는 큰따옴표', 'pins': BRAILLE_MAP['OPEN_QUOTE_DOUBLE']})
                is_dquote_open = True
            else:
                braille_sequence.append({'char': '닫는 큰따옴표', 'pins': BRAILLE_MAP['CLOSE_QUOTE_DOUBLE']})
                is_dquote_open = False

        # 5. 작은따옴표 (') 토글 처리
        elif char in ["'", '‘', '’']:
            if not is_squote_open:
                pins_1, pins_2 = BRAILLE_MAP['OPEN_QUOTE_SINGLE']
                braille_sequence.append({'char': '여는 작은따옴표(1/2)', 'pins': pins_1})
                braille_sequence.append({'char': '여는 작은따옴표(2/2)', 'pins': pins_2})
                is_squote_open = True
            else:
                pins_1, pins_2 = BRAILLE_MAP['CLOSE_QUOTE_SINGLE']
                braille_sequence.append({'char': '닫는 작은따옴표(1/2)', 'pins': pins_1})
                braille_sequence.append({'char': '닫는 작은따옴표(2/2)', 'pins': pins_2})
                is_squote_open = False

        # 6. 그 외 일반 문장부호 및 기호 처리
        elif char in BRAILLE_MAP:
            mapping = BRAILLE_MAP[char]
            if isinstance(mapping, tuple):
                braille_sequence.append({'char': f'기호 {char}(1/2)', 'pins': mapping[0]})
                braille_sequence.append({'char': f'기호 {char}(2/2)', 'pins': mapping[1]})
            else:
                braille_sequence.append({'char': f'기호 {char}', 'pins': mapping})
                
        else:
            braille_sequence.append({'char': f'미지원({char})', 'pins': BRAILLE_MAP[' ']})
            
    return braille_sequence

def process_braille_file(input_filename):
    """외부 텍스트 파일을 읽어와 점자 변환 데이터를 콘솔에 출력합니다."""
    if not os.path.exists(input_filename):
        print(f"오류: {input_filename} 파일이 존재하지 않습니다.")
        return

    with open(input_filename, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        
    print(f"--- 원본 텍스트 --- \n{content}\n")
    print("--- 하드웨어 변환 데이터 (모든 문장 부호 연동) ---")
    
    braille_data = text_to_braille_pins(content)
    
    for item in braille_data:
        print(f"문자: {item['char']:<18} -> 핀 신호: {item['pins']}") 