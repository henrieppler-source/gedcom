import os
import json
import re
import sqlite3
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

DB_FILE = os.path.join(os.path.dirname(__file__), 'gedcom.db')

MONTH_MAP = {
    'JAN': '01',
    'FEB': '02',
    'MAR': '03',
    'APR': '04',
    'MAY': '05',
    'JUN': '06',
    'JUL': '07',
    'AUG': '08',
    'SEP': '09',
    'OCT': '10',
    'NOV': '11',
    'DEC': '12',
}


class GedcomParser:
    @staticmethod
    def normalize_name(name: str) -> str:
        cleaned = re.sub(r'[/,;()\.]', ' ', name)
        return ' '.join(cleaned.strip().split()).lower()

    @staticmethod
    def normalize_date(date_text: str) -> str:
        return ' '.join(date_text.strip().split())

    @classmethod
    def _extract_date_signature(cls, date_text: str) -> dict:
        result = {'raw': '', 'day': '', 'month': '', 'year': '', 'canonical': ''}
        if not date_text:
            return result

        cleaned = date_text.strip()
        result['raw'] = cleaned
        text = re.sub(r'^\s*(ABT|BEF|AFT|CAL|EST|ABOUT|CA\.?|CIRCA|GEB\.?|GEST\.?|BORN|DIED)\s+', '', cleaned, flags=re.IGNORECASE)
        text = text.replace(',', ' ').replace('-', ' ').replace('/', ' ').replace('.', ' ')
        tokens = [token for token in text.split() if token]
        if not tokens:
            return result

        year_index = None
        for idx in range(len(tokens) - 1, -1, -1):
            if re.fullmatch(r'\d{4}', tokens[idx]):
                result['year'] = tokens[idx]
                year_index = idx
                break
        if not result['year']:
            return result

        before_year = tokens[:year_index]
        numeric_tokens = [token for token in before_year if token.isdigit()]
        month_tokens = [token for token in before_year if not token.isdigit()]

        if numeric_tokens:
            result['day'] = f"{int(numeric_tokens[0]):02d}"
            if len(numeric_tokens) >= 2:
                result['month'] = f"{int(numeric_tokens[1]):02d}"

        for token in month_tokens:
            token = token.upper()[:3]
            if token in MONTH_MAP:
                result['month'] = MONTH_MAP[token]
                break

        if result['day'] and result['month']:
            result['canonical'] = f"{result['day']}.{result['month']}.{result['year']}"
        elif result['month']:
            result['canonical'] = f"{result['month']}.{result['year']}"
        else:
            result['canonical'] = result['year']
        return result

    @classmethod
    def parse(cls, path: str) -> dict:
        individuals = {}
        families = {}

        with open(path, encoding='utf-8', errors='ignore') as handle:
            current = None
            context = None
            for raw in handle:
                line = raw.strip('\n\r')
                if not line:
                    continue
                parts = line.split(' ', 2)
                level = int(parts[0])
                if level == 0:
                    if len(parts) == 3 and parts[1].startswith('@'):
                        xref = parts[1]
                        tag = parts[2]
                    elif len(parts) == 2:
                        xref = None
                        tag = parts[1]
                    else:
                        xref = None
                        tag = parts[2] if len(parts) == 3 else ''
                    current = {'xref': xref, 'type': tag, 'data': {'NAME': '', 'BIRT_DATE': '', 'DEAT_DATE': '', 'FAMS': [], 'FAMC': [], 'HUSB': None, 'WIFE': None, 'CHIL': []}}
                    context = None
                else:
                    tag = parts[1] if len(parts) > 1 else ''
                    args = parts[2] if len(parts) > 2 else ''
                    if level == 1:
                        context = tag
                        if tag == 'NAME':
                            current['data']['NAME'] = args
                        elif tag in ('HUSB', 'WIFE'):
                            current['data'][tag] = args
                        elif tag == 'CHIL':
                            current['data']['CHIL'].append(args)
                        elif tag in ('FAMS', 'FAMC'):
                            current['data'][tag].append(args)
                    elif level == 2 and tag == 'DATE' and context in ('BIRT', 'DEAT'):
                        current['data'][f'{context}_DATE'] = args
                    elif level == 2 and context == 'NAME' and tag == 'SURN':
                        pass
                if level == 0 and current and current['type'] != 'HEAD':
                    if current['type'] == 'INDI':
                        individuals[current['xref']] = current['data']
                    elif current['type'] == 'FAM':
                        families[current['xref']] = current['data']
        return {'individuals': individuals, 'families': families}

    @classmethod
    def build_person_key(cls, record: dict) -> str:
        name = cls.normalize_name(record.get('NAME', ''))
        birth_signature = cls._extract_date_signature(record.get('BIRT_DATE', ''))
        birth = birth_signature['canonical'] or cls.normalize_date(record.get('BIRT_DATE', ''))
        return f'{name}|{birth}' if birth else name


class PDFParser:
    @staticmethod
    def _load_reader(path: str):
        try:
            import fitz
            return ('fitz', fitz.open(path))
        except Exception:
            try:
                from pypdf import PdfReader
                return ('pypdf', PdfReader(path))
            except Exception:
                try:
                    from PyPDF2 import PdfReader
                    return ('PyPDF2', PdfReader(path))
                except Exception as exc:
                    raise RuntimeError('Für den PDF-Import ist PyMuPDF oder pypdf/PyPDF2 erforderlich.') from exc

    @staticmethod
    def _clean_text(text: str) -> str:
        text = text.replace('\r', '\n')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def _round_coord(value: float, step: int = 10) -> int:
        return int(round(value / step) * step)

    @classmethod
    def _analyze_page(cls, page) -> dict:
        blocks = []
        try:
            raw_blocks = page.get_text('blocks')
        except Exception:
            raw_blocks = []

        for index, block in enumerate(raw_blocks, start=1):
            if len(block) < 5:
                continue
            x0, y0, x1, y1, text = block[:5]
            cleaned = cls._clean_text(text or '')
            if not cleaned:
                continue
            lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
            blocks.append({
                'block_no': index,
                'x0': x0,
                'y0': y0,
                'x1': x1,
                'y1': y1,
                'center_x': (x0 + x1) / 2,
                'center_y': (y0 + y1) / 2,
                'text': cleaned,
                'lines': lines,
            })

        if not blocks:
            fallback_text = cls._clean_text(page.get_text('text') or '')
            for index, line in enumerate([line.strip() for line in fallback_text.splitlines() if line.strip()], start=1):
                blocks.append({
                    'block_no': index,
                    'x0': 0,
                    'y0': index * 10,
                    'x1': 0,
                    'y1': index * 10,
                    'center_x': 0,
                    'center_y': index * 10,
                    'text': line,
                    'lines': [line],
                })

        blocks.sort(key=lambda item: (cls._round_coord(item['y0']), cls._round_coord(item['x0'])))
        column_markers = sorted({cls._round_coord(block['x0'], 100) for block in blocks})
        return {
            'blocks': blocks,
            'column_markers': column_markers,
            'reading_order': [{'block_no': block['block_no'], 'text': block['text']} for block in blocks],
        }

    @classmethod
    def _extract_pages(cls, path: str) -> list[dict]:
        backend, reader = cls._load_reader(path)
        pages = []
        if backend == 'fitz':
            try:
                for page_index, page in enumerate(reader, start=1):
                    analysis = cls._analyze_page(page)
                    pages.append({
                        'page_no': page_index,
                        'text': '\n\n'.join(block['text'] for block in analysis['blocks']),
                        'analysis': analysis,
                    })
            finally:
                reader.close()
        else:
            for page_index, page in enumerate(reader.pages, start=1):
                text = cls._clean_text(page.extract_text() or '')
                analysis_blocks = []
                for index, line in enumerate([line.strip() for line in text.splitlines() if line.strip()], start=1):
                    analysis_blocks.append({
                        'block_no': index,
                        'x0': 0,
                        'y0': index * 10,
                        'x1': 0,
                        'y1': index * 10,
                        'center_x': 0,
                        'center_y': index * 10,
                        'text': line,
                        'lines': [line],
                    })
                pages.append({
                    'page_no': page_index,
                    'text': text,
                    'analysis': {
                        'blocks': analysis_blocks,
                        'column_markers': [],
                        'reading_order': [{'block_no': block['block_no'], 'text': block['text']} for block in analysis_blocks],
                    },
                })
        return pages

    @staticmethod
    def _display_name(name: str) -> str:
        raw = (name or '').strip()
        if '/' in raw:
            parts = [part.strip() for part in raw.split('/') if part.strip()]
            if len(parts) >= 2:
                return f"{parts[1]} / {parts[0]}"
        return raw

    @staticmethod
    def _normalize_label(text: str) -> str:
        return re.sub(r'[^a-z0-9]+', ' ', (text or '').lower()).strip()

    @staticmethod
    def _find_label_value(text: str, labels: list[str]) -> str:
        if not text:
            return ''
        for label in labels:
            pattern = re.compile(rf'(?:^|[\s;,\-]){label}\s*[:\-]?\s*(.+?)(?=(?:\s{1,}|$))', re.IGNORECASE)
            match = pattern.search(text)
            if match:
                value = match.group(1).strip(' .;,-')
                if value:
                    return value
        return ''

    @classmethod
    def _parse_event_value(cls, text: str, labels: list[str]) -> tuple[str, str]:
        value = cls._find_label_value(text, labels)
        if not value:
            return '', ''
        date_match = re.search(r'(\d{1,2}\s+[A-ZÄÖÜ]{3}\s+\d{4}|\d{1,2}\.\d{1,2}\.\d{4}|\d{4})', value, flags=re.IGNORECASE)
        if date_match:
            date_text = date_match.group(1).upper()
            rest = value.replace(date_match.group(1), '').strip(' .;,-')
            return date_text, rest
        return '', value

    @staticmethod
    def _looks_like_emigration_start(line: str) -> bool:
        raw = ' '.join((line or '').split())
        if not raw or ',' not in raw:
            return False
        if raw.lower().startswith(('quelle:', 'bemerkungen:', 'beruf:', 'aus:', 'alter oder geburtsdatum:')):
            return False
        first_part = raw.split(',', 1)[0].strip()
        second_part = raw.split(',', 1)[1].strip() if ',' in raw else ''
        return bool(first_part) and bool(second_part)

    @staticmethod
    def _split_emigration_name(line: str) -> tuple[str, str, str]:
        raw = ' '.join((line or '').split())
        if not raw or ',' not in raw:
            return '', '', ''

        parts = [part.strip() for part in raw.split(',') if part.strip()]
        if len(parts) < 2:
            return '', '', ''

        surname = parts[0]
        given_names = parts[1]
        tail = ', '.join(parts[2:]).strip()
        if tail.lower().startswith(('geb', 'geb.', 'geb ')):
            tail = tail.split(':', 1)[-1].strip() if ':' in tail else tail[3:].strip(' .,:;')
        return surname, given_names, tail

    @classmethod
    def _parse_profile_block(cls, text: str) -> dict | None:
        raw = cls._clean_text(text or '')
        if not raw:
            return None

        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            return None

        name_line = lines[0]
        candidate_name = ''
        if '/' in name_line or ',' in name_line:
            candidate_name = name_line
        else:
            for line in lines[:3]:
                if '/' in line or (line and line.count(' ') >= 1 and any(ch.isupper() for ch in line)):
                    candidate_name = line
                    break
        if not candidate_name:
            candidate_name = lines[0]

        display_name = cls._display_name(candidate_name)
        if not display_name:
            return None

        person_name = display_name
        surname = ''
        given_names = ''
        if ' / ' in display_name:
            surname, given_names = [part.strip() for part in display_name.split(' / ', 1)]
        elif '/' in candidate_name:
            parts = [part.strip() for part in candidate_name.split('/') if part.strip()]
            if len(parts) >= 2:
                given_names = parts[0]
                surname = parts[1]
        elif ',' in candidate_name:
            surname, given_names = [part.strip() for part in candidate_name.split(',', 1)]
        else:
            tokens = candidate_name.split()
            if len(tokens) >= 2:
                given_names = ' '.join(tokens[:-1])
                surname = tokens[-1]

        birth_date, birth_place = cls._parse_event_value(raw, ['geb', 'geboren am', 'geboren', 'birth', 'b.'])
        death_date, death_place = cls._parse_event_value(raw, ['gest', 'gestorben am', 'gestorben', 'death', 'd.'])
        emigration_date, emigration_place = cls._parse_event_value(raw, ['ausgewandert am', 'ausgewandert', 'emigriert am', 'emigriert', 'ausgewandert nach', 'wanderte aus am'])
        marriage_date, marriage_place = cls._parse_event_value(raw, ['verheiratet am', 'verheiratet', 'heiratete am', 'heiratete', 'oo', 'ehe'])
        residence = cls._find_label_value(raw, ['wohnort', 'wohnte in', 'wohnhaft in', 'residierte in'])
        origin = cls._find_label_value(raw, ['herkunft', 'geboren in', 'geburtsort'])
        destination = cls._find_label_value(raw, ['ziel', 'zielort', 'nach', 'nach amerika', 'nach usa', 'nach kanada', 'nach brasilien'])

        event_notes = []
        for label, value in [
            ('Birth', birth_date or birth_place),
            ('Death', death_date or death_place),
            ('Emigration', emigration_date or emigration_place),
            ('Marriage', marriage_date or marriage_place),
            ('Residence', residence),
            ('Origin', origin),
            ('Destination', destination),
        ]:
            if value:
                event_notes.append(f'{label}: {value}')

        return {
            'record_type': 'person',
            'display_name': person_name,
            'given_names': given_names,
            'surname': surname,
            'birth': birth_date,
            'death': death_date,
            'emigration_date': emigration_date,
            'emigration_place': emigration_place,
            'marriage_date': marriage_date,
            'marriage_place': marriage_place,
            'residence': residence,
            'origin': origin,
            'destination': destination,
            'raw_text': raw,
            'search_key': GedcomParser.normalize_name(candidate_name),
            'date_fragment': emigration_date or birth_date or death_date or marriage_date,
            'summary': '; '.join(event_notes),
        }

    @classmethod
    def _parse_emigration_block(cls, text: str) -> dict | None:
        raw = cls._clean_text(text or '')
        if not raw:
            return None
        lower = raw.lower()
        if not any(token in lower for token in ['aus gewandert nach', 'ausgewandert nach', 'alter oder geburtsdatum', 'quelle:', 'bemerkungen:', 'beruf:', 'aus:']):
            return None

        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            return None

        surname, given_names, extra = cls._split_emigration_name(lines[0])
        if not surname or not given_names:
            return None

        maiden_name = ''
        if extra.lower().startswith('geb'):
            maiden_name = extra.split('.', 1)[-1].strip() if '.' in extra else extra[3:].strip(': ').strip()

        combined = ' '.join(lines).strip()
        combined = re.sub(r'\ba\s+us\b', 'aus', combined, flags=re.IGNORECASE)
        combined = re.sub(r'\bAlter\s+oder\s+Geburtsdatum\s*:\s*', 'Alter oder Geburtsdatum: ', combined, flags=re.IGNORECASE)
        combined = re.sub(r'\bBeruf\s*:\s*', 'Beruf: ', combined, flags=re.IGNORECASE)
        combined = re.sub(r'\baus\s*:\s*', 'aus: ', combined, flags=re.IGNORECASE)
        combined = re.sub(r'\baus\s+gewandert\s+nac?h\s*:\s*', 'aus gewandert nach: ', combined, flags=re.IGNORECASE)
        combined = re.sub(r'\bausgewandert\s+nac?h\s*:\s*', 'ausgewandert nach: ', combined, flags=re.IGNORECASE)
        combined = re.sub(r'\bBemerkungen?\s*:\s*', 'Bemerkungen: ', combined, flags=re.IGNORECASE)
        combined = re.sub(r'\bQuelle\s*:\s*', 'Quelle: ', combined, flags=re.IGNORECASE)
        combined = re.sub(r'\sim\s+Jahre\s+', ' im Jahre ', combined, flags=re.IGNORECASE)

        def first_match(patterns: list[str]) -> str:
            for pattern in patterns:
                m = re.search(pattern, combined, flags=re.IGNORECASE)
                if m:
                    return m.group(1).strip(' .;,-')
            return ''

        occupation = first_match([r'Beruf:\s*(.+?)\s*(?=Alter oder Geburtsdatum:|aus:|aus gewandert nach:|ausgewandert nach:|Bemerkungen?:|Quelle:|$)'])
        age_or_birth = first_match([r'Alter oder Geburtsdatum:\s*(.+?)\s*(?=aus:|aus gewandert nach:|ausgewandert nach:|Bemerkungen?:|Quelle:|$)'])
        origin = first_match([r'aus:\s*(.+?)\s*(?=aus gewandert nach:|ausgewandert nach:|im Jahre|Bemerkungen?:|Quelle:|$)'])
        destination = first_match([r'aus gewandert nach:\s*(.+?)\s*(?=im Jahre|Bemerkungen?:|Quelle:|$)', r'ausgewandert nach:\s*(.+?)\s*(?=im Jahre|Bemerkungen?:|Quelle:|$)'])
        remarks = first_match([r'Bemerkungen:\s*(.+?)\s*(?=Quelle:|$)'])
        source = first_match([r'Quelle:\s*(.+?)\s*$'])
        year_match = re.search(r'im Jahre\s+(\d{4})', combined, flags=re.IGNORECASE)
        application_year = year_match.group(1) if year_match else ''

        display_name = f'{surname} / {given_names}'

        summary_parts = []
        if age_or_birth:
            summary_parts.append(f'Alter/Geburtsdatum: {age_or_birth}')
        if maiden_name:
            summary_parts.append(f'Geburtsname: {maiden_name}')
        if origin:
            summary_parts.append(f'aus: {origin}')
        if destination:
            summary_parts.append(f'ausgewandert nach: {destination}')
        if application_year:
            summary_parts.append(f'im Jahre {application_year}')
        if occupation:
            summary_parts.append(f'Beruf: {occupation}')
        if remarks:
            summary_parts.append(f'Bemerkungen: {remarks}')
        if source:
            summary_parts.append(f'Quelle: {source}')
        if maiden_name:
            summary_parts.append(f'Geburtsname: {maiden_name}')

        return {
            'record_type': 'person',
            'display_name': display_name,
            'given_names': given_names,
            'surname': surname,
            'birth': '',
            'death': '',
            'emigration_date': application_year,
            'emigration_place': destination,
            'marriage_date': '',
            'marriage_place': '',
            'residence': origin,
            'origin': origin,
            'destination': destination,
            'age_or_birth': age_or_birth,
            'occupation': occupation,
            'remarks': remarks,
            'source': source,
            'maiden_name': maiden_name,
            'raw_text': raw,
            'search_key': GedcomParser.normalize_name(f'{surname} {given_names}'),
            'date_fragment': application_year or age_or_birth,
            'summary': '; '.join(summary_parts),
        }

    @staticmethod
    def _compose_basic_summary(birth: str, death: str) -> str:
        parts = []
        if birth:
            parts.append(f'Birth: {birth}')
        if death:
            parts.append(f'Death: {death}')
        return '; '.join(parts)

    @staticmethod
    def _split_date_segment(text: str) -> tuple[str, str]:
        if not text:
            return '', ''
        cleaned = text.strip()
        if not cleaned:
            return '', ''
        year_match = re.search(r'(\d{4})\s*$', cleaned)
        if year_match:
            year = year_match.group(1)
            prefix = cleaned[:year_match.start()].strip(' .,-;')
            return prefix, year
        return cleaned, ''

    @classmethod
    def _parse_person_line(cls, line: str) -> dict | None:
        raw = ' '.join(line.strip().split())
        if not raw:
            return None

        name_part = raw
        birth = ''
        death = ''
        if '|' in raw:
            chunks = [chunk.strip() for chunk in raw.split('|') if chunk.strip()]
            if chunks:
                name_part = chunks[0]
                for chunk in chunks[1:]:
                    lowered = chunk.lower()
                    if lowered.startswith('geb'):
                        birth = chunk.split('.', 1)[-1].strip() if '.' in chunk else chunk[3:].strip(': ').strip()
                    elif lowered.startswith('birth'):
                        birth = chunk.split(':', 1)[-1].strip() if ':' in chunk else chunk[5:].strip()
                    elif lowered.startswith('gest'):
                        death = chunk.split('.', 1)[-1].strip() if '.' in chunk else chunk[4:].strip(': ').strip()
                    elif lowered.startswith('death'):
                        death = chunk.split(':', 1)[-1].strip() if ':' in chunk else chunk[5:].strip()

        if not birth:
            birth_match = re.search(r'\b(?:geb\.?|born|birth)\s*[:\-]?\s*(.+)$', raw, flags=re.IGNORECASE)
            if birth_match:
                birth = birth_match.group(1).strip()
        if not death:
            death_match = re.search(r'\b(?:gest\.?|died|death)\s*[:\-]?\s*(.+)$', raw, flags=re.IGNORECASE)
            if death_match:
                death = death_match.group(1).strip()

        date_fragment = ''
        if birth:
            date_fragment = birth
        elif death:
            date_fragment = death

        given_names = ''
        surname = ''
        if '/' in name_part:
            parts = [part.strip() for part in name_part.split('/') if part.strip()]
            if len(parts) >= 2:
                given_names = parts[0]
                surname = parts[1]
        elif ',' in name_part:
            surname, given_names = [part.strip() for part in name_part.split(',', 1)]
        else:
            tokens = name_part.split()
            if len(tokens) >= 2:
                given_names = ' '.join(tokens[:-1])
                surname = tokens[-1]

        if not (given_names or surname):
            return None

        normalized_display = cls._display_name(name_part)
        return {
            'record_type': 'person',
            'display_name': normalized_display,
            'given_names': given_names,
            'surname': surname,
            'birth': birth,
            'death': death,
            'emigration_date': '',
            'emigration_place': '',
            'marriage_date': '',
            'marriage_place': '',
            'residence': '',
            'origin': '',
            'destination': '',
            'raw_text': raw,
            'search_key': GedcomParser.normalize_name(name_part),
            'date_fragment': date_fragment,
            'summary': cls._compose_basic_summary(birth, death),
        }

    @classmethod
    def extract_records(cls, path: str) -> dict:
        pages = cls._extract_pages(path)
        records = []
        line_count = 0
        person_count = 0
        for page in pages:
            blocks = page.get('analysis', {}).get('blocks', [])
            if not blocks:
                blocks = [{'block_no': idx, 'lines': [line], 'text': line} for idx, line in enumerate([line.strip() for line in page['text'].splitlines() if line.strip()], start=1)]
            page_text = page.get('text', '')
            emigration_mode = any(token in page_text.lower() for token in ['aus gewandert nach', 'ausgewandert nach', 'alter oder geburtsdatum', 'bemerkungen:', 'quelle:'])

            if emigration_mode:
                current_lines: list[str] = []
                current_block_no = 0
                current_line_no = 0
                record_index = 0

                def flush_current():
                    nonlocal current_lines, current_block_no, current_line_no, record_index, person_count, line_count
                    if not current_lines:
                        return
                    block_text = '\n'.join(current_lines).strip()
                    parsed_block = cls._parse_emigration_block(block_text)
                    if parsed_block:
                        person_count += 1
                        line_count += len(current_lines)
                        record_index += 1
                        parsed_block.update({
                            'page_no': page['page_no'],
                            'line_no': current_line_no or record_index,
                            'block_no': current_block_no,
                            'block_text': block_text,
                        })
                        records.append(parsed_block)
                    current_lines = []
                    current_block_no = 0
                    current_line_no = 0

                for block in blocks:
                    block_no = block.get('block_no', 0)
                    for line in [entry.strip() for entry in block.get('lines', []) if entry.strip()]:
                        if cls._looks_like_emigration_start(line):
                            flush_current()
                            current_lines = [line]
                            current_block_no = block_no
                            current_line_no = record_index + 1
                        elif current_lines:
                            current_lines.append(line)
                        else:
                            continue
                flush_current()
                continue

            order_no = 0
            for block in blocks:
                block_text = block.get('text', '')
                parsed_block = cls._parse_profile_block(block_text)
                if parsed_block:
                    person_count += 1
                    line_count += max(1, len(block.get('lines', [])))
                    parsed_block.update({
                        'page_no': page['page_no'],
                        'line_no': order_no + 1,
                        'block_no': block.get('block_no', 0),
                        'block_text': block_text,
                    })
                    records.append(parsed_block)
                    order_no += max(1, len(block.get('lines', [])))
                    continue

                for line in block.get('lines', []):
                    order_no += 1
                    line_count += 1
                    parsed = cls._parse_person_line(line)
                    base_record = {
                        'page_no': page['page_no'],
                        'line_no': order_no,
                        'block_no': block.get('block_no', 0),
                        'block_text': block_text,
                    }
                    if parsed:
                        person_count += 1
                        parsed.update(base_record)
                        records.append(parsed)
        return {'pages': pages, 'records': records, 'line_count': line_count, 'person_count': person_count}


class GedcomDatabase:
    def __init__(self, path: str):
        self.path = path
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self):
        cursor = self.connection.cursor()
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS gedcom_files (id INTEGER PRIMARY KEY, path TEXT UNIQUE, name TEXT, imported_at TEXT)'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS individuals (id INTEGER PRIMARY KEY, file_id INTEGER, xref TEXT, name TEXT, birth TEXT, death TEXT, normalized_key TEXT, famc TEXT, fams TEXT, FOREIGN KEY (file_id) REFERENCES gedcom_files(id))'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS families (id INTEGER PRIMARY KEY, file_id INTEGER, xref TEXT, husband_xref TEXT, wife_xref TEXT, children_xrefs TEXT, FOREIGN KEY (file_id) REFERENCES gedcom_files(id))'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS pdf_files (id INTEGER PRIMARY KEY, path TEXT UNIQUE, name TEXT, imported_at TEXT)'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS pdf_pages (id INTEGER PRIMARY KEY, file_id INTEGER, page_no INTEGER, text TEXT, analysis TEXT, FOREIGN KEY (file_id) REFERENCES pdf_files(id))'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS pdf_records (id INTEGER PRIMARY KEY, file_id INTEGER, page_no INTEGER, block_no INTEGER, line_no INTEGER, record_type TEXT, display_name TEXT, given_names TEXT, surname TEXT, birth TEXT, death TEXT, emigration_date TEXT, emigration_place TEXT, marriage_date TEXT, marriage_place TEXT, residence TEXT, origin TEXT, destination TEXT, age_or_birth TEXT, occupation TEXT, remarks TEXT, source TEXT, maiden_name TEXT, raw_text TEXT, search_key TEXT, date_fragment TEXT, summary TEXT, FOREIGN KEY (file_id) REFERENCES pdf_files(id))'
        )
        self.connection.commit()
        self._upgrade_schema()

    def _upgrade_schema(self):
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA table_info(individuals)")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'famc' not in columns:
            cursor.execute('ALTER TABLE individuals ADD COLUMN famc TEXT')
        if 'fams' not in columns:
            cursor.execute('ALTER TABLE individuals ADD COLUMN fams TEXT')
        cursor.execute("PRAGMA table_info(pdf_pages)")
        page_columns = [row['name'] for row in cursor.fetchall()]
        if 'analysis' not in page_columns:
            cursor.execute('ALTER TABLE pdf_pages ADD COLUMN analysis TEXT')
        cursor.execute("PRAGMA table_info(pdf_records)")
        record_columns = [row['name'] for row in cursor.fetchall()]
        if 'block_no' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN block_no INTEGER')
        if 'emigration_date' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN emigration_date TEXT')
        if 'emigration_place' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN emigration_place TEXT')
        if 'marriage_date' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN marriage_date TEXT')
        if 'marriage_place' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN marriage_place TEXT')
        if 'residence' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN residence TEXT')
        if 'origin' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN origin TEXT')
        if 'destination' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN destination TEXT')
        if 'age_or_birth' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN age_or_birth TEXT')
        if 'occupation' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN occupation TEXT')
        if 'remarks' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN remarks TEXT')
        if 'source' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN source TEXT')
        if 'maiden_name' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN maiden_name TEXT')
        if 'summary' not in record_columns:
            cursor.execute('ALTER TABLE pdf_records ADD COLUMN summary TEXT')
        self.connection.commit()

    def add_gedcom_file(self, path: str) -> int:
        file_path = os.path.abspath(path)
        name = os.path.basename(file_path)
        now = datetime.datetime.now().isoformat()
        cursor = self.connection.cursor()
        cursor.execute('INSERT OR IGNORE INTO gedcom_files (path, name, imported_at) VALUES (?, ?, ?)', (file_path, name, now))
        self.connection.commit()
        cursor.execute('SELECT id FROM gedcom_files WHERE path = ?', (file_path,))
        row = cursor.fetchone()
        return row['id'] if row else 0

    def add_pdf_file(self, path: str) -> int:
        file_path = os.path.abspath(path)
        name = os.path.basename(file_path)
        now = datetime.datetime.now().isoformat()
        cursor = self.connection.cursor()
        cursor.execute('INSERT OR IGNORE INTO pdf_files (path, name, imported_at) VALUES (?, ?, ?)', (file_path, name, now))
        self.connection.commit()
        cursor.execute('SELECT id FROM pdf_files WHERE path = ?', (file_path,))
        row = cursor.fetchone()
        return row['id'] if row else 0

    def delete_pdf_data(self, file_id: int):
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM pdf_pages WHERE file_id = ?', (file_id,))
        cursor.execute('DELETE FROM pdf_records WHERE file_id = ?', (file_id,))
        self.connection.commit()

    def import_pdf(self, path: str) -> dict:
        extracted = PDFParser.extract_records(path)
        file_id = self.add_pdf_file(path)
        self.delete_pdf_data(file_id)
        cursor = self.connection.cursor()
        for page in extracted['pages']:
            cursor.execute(
                'INSERT INTO pdf_pages (file_id, page_no, text, analysis) VALUES (?, ?, ?, ?)',
                (file_id, page['page_no'], page['text'], json.dumps(page.get('analysis', {}), ensure_ascii=False)),
            )
        for record in extracted['records']:
            cursor.execute(
                'INSERT INTO pdf_records (file_id, page_no, block_no, line_no, record_type, display_name, given_names, surname, birth, death, emigration_date, emigration_place, marriage_date, marriage_place, residence, origin, destination, age_or_birth, occupation, remarks, source, maiden_name, raw_text, search_key, date_fragment, summary) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    file_id,
                    record['page_no'],
                    record.get('block_no', 0),
                    record['line_no'],
                    record['record_type'],
                    record['display_name'],
                    record['given_names'],
                    record['surname'],
                    record['birth'],
                    record['death'],
                    record.get('emigration_date', ''),
                    record.get('emigration_place', ''),
                    record.get('marriage_date', ''),
                    record.get('marriage_place', ''),
                    record.get('residence', ''),
                    record.get('origin', ''),
                    record.get('destination', ''),
                    record.get('age_or_birth', ''),
                    record.get('occupation', ''),
                    record.get('remarks', ''),
                    record.get('source', ''),
                    record.get('maiden_name', ''),
                    record['raw_text'],
                    record['search_key'],
                    record['date_fragment'],
                    record.get('summary', ''),
                ),
            )
        now = datetime.datetime.now().isoformat()
        cursor.execute('UPDATE pdf_files SET imported_at = ? WHERE id = ?', (now, file_id))
        self.connection.commit()
        return {
            'file_id': file_id,
            'file_name': os.path.basename(os.path.abspath(path)),
            'pages': len(extracted['pages']),
            'lines': extracted['line_count'],
            'persons': extracted['person_count'],
        }

    def list_pdf_files(self) -> list[sqlite3.Row]:
        cursor = self.connection.cursor()
        cursor.execute('SELECT id, path, name, imported_at FROM pdf_files ORDER BY imported_at DESC')
        return cursor.fetchall()

    def get_pdf_file_summary(self, file_id: int) -> dict:
        cursor = self.connection.cursor()
        cursor.execute('SELECT name FROM pdf_files WHERE id = ?', (file_id,))
        row = cursor.fetchone()
        if not row:
            return {'name': '', 'pages': 0, 'records': 0, 'persons': 0}
        cursor.execute('SELECT COUNT(*) AS total FROM pdf_pages WHERE file_id = ?', (file_id,))
        pages = cursor.fetchone()['total']
        cursor.execute('SELECT COUNT(*) AS total FROM pdf_records WHERE file_id = ?', (file_id,))
        records = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) AS total FROM pdf_records WHERE file_id = ? AND record_type = 'person'", (file_id,))
        persons = cursor.fetchone()['total']
        return {'name': row['name'], 'pages': pages, 'records': records, 'persons': persons}

    def get_pdf_records(self, file_id: int, query: str = '', surname: str = '', given: str = '') -> list[sqlite3.Row]:
        cursor = self.connection.cursor()
        sql = [
            'SELECT page_no, block_no, line_no, record_type, display_name, given_names, surname, birth, death, emigration_date, emigration_place, marriage_date, marriage_place, residence, origin, destination, age_or_birth, occupation, remarks, source, maiden_name, raw_text, search_key, date_fragment, summary',
            'FROM pdf_records',
            'WHERE file_id = ? AND record_type = \'person\'',
        ]
        params: list[str | int] = [file_id]

        if query:
            sql.append('AND (display_name LIKE ? OR raw_text LIKE ? OR birth LIKE ? OR death LIKE ? OR emigration_date LIKE ? OR emigration_place LIKE ? OR marriage_date LIKE ? OR marriage_place LIKE ? OR residence LIKE ? OR origin LIKE ? OR destination LIKE ? OR age_or_birth LIKE ? OR occupation LIKE ? OR remarks LIKE ? OR source LIKE ? OR maiden_name LIKE ? OR summary LIKE ? OR surname LIKE ? OR given_names LIKE ?)')
            like = f'%{query}%'
            params.extend([like] * 19)
        if surname:
            sql.append('AND surname LIKE ?')
            params.append(f'%{surname}%')
        if given:
            sql.append('AND given_names LIKE ?')
            params.append(f'%{given}%')

        sql.append('ORDER BY surname COLLATE NOCASE, given_names COLLATE NOCASE, page_no, line_no')
        cursor.execute(' '.join(sql), params)
        return cursor.fetchall()

    def delete_file_data(self, file_id: int):
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM individuals WHERE file_id = ?', (file_id,))
        cursor.execute('DELETE FROM families WHERE file_id = ?', (file_id,))
        self.connection.commit()

    def import_file(self, path: str) -> int:
        parsed = GedcomParser.parse(path)
        file_id = self.add_gedcom_file(path)
        self.delete_file_data(file_id)
        cursor = self.connection.cursor()
        for xref, person in parsed['individuals'].items():
            key = GedcomParser.build_person_key(person)
            famc = '|'.join(person.get('FAMC', []))
            fams = '|'.join(person.get('FAMS', []))
            cursor.execute(
                'INSERT INTO individuals (file_id, xref, name, birth, death, normalized_key, famc, fams) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (file_id, xref, person.get('NAME', ''), person.get('BIRT_DATE', ''), person.get('DEAT_DATE', ''), key, famc, fams),
            )
        for xref, family in parsed['families'].items():
            children = '|'.join(family.get('CHIL', []))
            cursor.execute(
                'INSERT INTO families (file_id, xref, husband_xref, wife_xref, children_xrefs) VALUES (?, ?, ?, ?, ?)',
                (file_id, xref, family.get('HUSB'), family.get('WIFE'), children),
            )
        now = datetime.datetime.now().isoformat()
        cursor.execute('UPDATE gedcom_files SET imported_at = ? WHERE id = ?', (now, file_id))
        self.connection.commit()
        return file_id

    def list_files(self) -> list[sqlite3.Row]:
        cursor = self.connection.cursor()
        cursor.execute('SELECT id, path, name, imported_at FROM gedcom_files ORDER BY imported_at DESC')
        return cursor.fetchall()

    def file_summary(self, file_id: int) -> dict:
        cursor = self.connection.cursor()
        cursor.execute('SELECT COUNT(*) AS total FROM individuals WHERE file_id = ?', (file_id,))
        individuals = cursor.fetchone()['total']
        cursor.execute('SELECT COUNT(*) AS total FROM families WHERE file_id = ?', (file_id,))
        families = cursor.fetchone()['total']
        cursor.execute('SELECT name FROM gedcom_files WHERE id = ?', (file_id,))
        row = cursor.fetchone()
        return {'name': row['name'] if row else '', 'individuals': individuals, 'families': families}

    def get_individuals(self, file_id: int) -> list[sqlite3.Row]:
        cursor = self.connection.cursor()
        cursor.execute('SELECT id, xref, name, birth, death, normalized_key, famc, fams FROM individuals WHERE file_id = ?', (file_id,))
        return cursor.fetchall()

    def get_families(self, file_id: int) -> list[sqlite3.Row]:
        cursor = self.connection.cursor()
        cursor.execute('SELECT xref, husband_xref, wife_xref, children_xrefs FROM families WHERE file_id = ?', (file_id,))
        return cursor.fetchall()

    def build_family_relations(self, file_id: int) -> dict:
        individuals = {row['xref']: {**row} for row in self.get_individuals(file_id)}
        families = {row['xref']: {**row} for row in self.get_families(file_id)}

        for person in individuals.values():
            person['parents'] = []
            person['children'] = []
            person['spouses'] = []

        for fam in families.values():
            children = fam['children_xrefs'].split('|') if fam['children_xrefs'] else []
            if fam['husband_xref'] and fam['husband_xref'] in individuals:
                individuals[fam['husband_xref']]['spouses'].append(fam['wife_xref'])
            if fam['wife_xref'] and fam['wife_xref'] in individuals:
                individuals[fam['wife_xref']]['spouses'].append(fam['husband_xref'])
            for child_xref in children:
                if child_xref in individuals:
                    individuals[child_xref]['parents'].extend([fam['husband_xref'], fam['wife_xref']])
                    if fam['husband_xref'] in individuals:
                        individuals[fam['husband_xref']]['children'].append(child_xref)
                    if fam['wife_xref'] in individuals:
                        individuals[fam['wife_xref']]['children'].append(child_xref)

        for person in individuals.values():
            person['parents'] = [xref for xref in set(person['parents']) if xref and xref in individuals]
            person['children'] = [xref for xref in set(person['children']) if xref and xref in individuals]
            person['spouses'] = [xref for xref in set(person['spouses']) if xref and xref in individuals]

        for person in individuals.values():
            surnames = re.sub(r'[/,;()\.]', ' ', person['name']).split()
            person['surname'] = surnames[-1].lower() if surnames else ''
            person['birth_year'] = ''
            birth_year = self._extract_year(person['birth'])
            if birth_year:
                person['birth_year'] = birth_year
        return individuals

    def _normalize_search_name(self, text: str) -> str:
        return GedcomParser.normalize_name(text)

    def _extract_year(self, date_text: str) -> str:
        if not date_text:
            return ''
        matches = re.findall(r'(\d{4})', date_text)
        return matches[-1] if matches else ''

    def _extract_date_signature(self, date_text: str) -> dict:
        result = {'raw': '', 'day': '', 'month': '', 'year': '', 'canonical': ''}
        if not date_text:
            return result

        cleaned = date_text.strip()
        result['raw'] = cleaned
        text = re.sub(r'^\s*(ABT|BEF|AFT|CAL|EST|ABOUT|CA\.?|CIRCA|GEB\.?|GEST\.?|BORN|DIED)\s+', '', cleaned, flags=re.IGNORECASE)
        text = text.replace(',', ' ').replace('-', ' ').replace('/', ' ').replace('.', ' ')
        tokens = [token for token in text.split() if token]
        if not tokens:
            return result

        year_index = None
        for idx in range(len(tokens) - 1, -1, -1):
            if re.fullmatch(r'\d{4}', tokens[idx]):
                result['year'] = tokens[idx]
                year_index = idx
                break
        if not result['year']:
            return result

        before_year = tokens[:year_index]
        numeric_tokens = [token for token in before_year if token.isdigit()]
        month_tokens = [token for token in before_year if not token.isdigit()]

        if numeric_tokens:
            result['day'] = f"{int(numeric_tokens[0]):02d}"
            if len(numeric_tokens) >= 2:
                result['month'] = f"{int(numeric_tokens[1]):02d}"

        for token in month_tokens:
            token = token.upper()[:3]
            if token in MONTH_MAP:
                result['month'] = MONTH_MAP[token]
                break

        if result['day'] and result['month']:
            result['canonical'] = f"{result['day']}.{result['month']}.{result['year']}"
        elif result['month']:
            result['canonical'] = f"{result['month']}.{result['year']}"
        else:
            result['canonical'] = result['year']
        return result

    def _parse_person_query(self, query: str) -> dict:
        text = ' '.join(query.replace(';', ' ').replace('|', ' ').split())
        parsed = {
            'name': '',
            'birth': '',
            'death': '',
            'birth_year': '',
            'death_year': '',
        }

        labeled_birth = re.search(
            r'(?:geb(?:\.|oren)?|birth|birt|born)\s*[:\-]?\s*([0-9]{1,2}[.\-/ ]+[A-Za-zÄÖÜäöü0-9]{1,9}[.\-/ ]+\d{4}|\d{4})',
            text,
            flags=re.IGNORECASE,
        )
        labeled_death = re.search(
            r'(?:gest(?:\.|orben)?|death|deat|died)\s*[:\-]?\s*([0-9]{1,2}[.\-/ ]+[A-Za-zÄÖÜäöü0-9]{1,9}[.\-/ ]+\d{4}|\d{4})',
            text,
            flags=re.IGNORECASE,
        )
        if labeled_birth:
            parsed['birth'] = labeled_birth.group(1).strip()
        if labeled_death:
            parsed['death'] = labeled_death.group(1).strip()

        for match in re.finditer(r'([0-9]{1,2}[.\-/ ]+[A-Za-zÄÖÜäöü0-9]{1,9}[.\-/ ]+\d{4}|\d{4})', text):
            value = match.group(1).strip()
            if not parsed['birth']:
                parsed['birth'] = value
            elif not parsed['death'] and value != parsed['birth']:
                parsed['death'] = value

        name_text = text
        if parsed['birth']:
            name_text = name_text.replace(parsed['birth'], ' ')
        if parsed['death']:
            name_text = name_text.replace(parsed['death'], ' ')
        name_text = re.sub(r'\b(geb(?:\.|oren)?|gest(?:\.|orben)?|birth|death|birt|deat|born|died)\b', ' ', name_text, flags=re.IGNORECASE)
        parsed['name'] = ' '.join(name_text.split())
        parsed['birth_year'] = self._extract_year(parsed['birth'])
        parsed['death_year'] = self._extract_year(parsed['death'])
        return parsed

    def _person_query_score(self, person: dict, query: dict) -> int:
        score = 0
        name_query = self._normalize_search_name(query['name'])
        person_name = self._normalize_search_name(person['name'])

        if name_query and name_query == person_name:
            score += 20
        elif name_query and name_query in person_name:
            score += 10
        elif person_name and person_name in name_query:
            score += 8
        else:
            query_tokens = set(name_query.split())
            person_tokens = set(person_name.split())
            overlap = len(query_tokens & person_tokens)
            if overlap:
                score += overlap * 3

        if query['birth']:
            query_birth = self._extract_date_signature(query['birth'])
            person_birth = self._extract_date_signature(person['birth'])
            if query_birth['canonical'] and person_birth['canonical'] and query_birth['canonical'] == person_birth['canonical']:
                score += 15
            elif query_birth['year'] and person_birth['year'] and query_birth['year'] == person_birth['year']:
                score += 6
            elif query_birth['year'] and person_birth['year'] and abs(int(query_birth['year']) - int(person_birth['year'])) <= 1:
                score += 2

        if query['death']:
            query_death = self._extract_date_signature(query['death'])
            person_death = self._extract_date_signature(person['death'])
            if query_death['canonical'] and person_death['canonical'] and query_death['canonical'] == person_death['canonical']:
                score += 12
            elif query_death['year'] and person_death['year'] and query_death['year'] == person_death['year']:
                score += 4

        if query['birth_year'] and person['birth_year'] and query['birth_year'] == person['birth_year']:
            score += 6
        if query['death_year'] and person['death_year'] and query['death_year'] == person['death_year']:
            score += 4
        if query['birth_year'] and person['birth_year'] and abs(int(query['birth_year']) - int(person['birth_year'])) <= 1:
            score += 1

        return score

    def _find_person_matches(self, relations: dict, query: str) -> list[tuple[int, dict]]:
        parsed = self._parse_person_query(query)
        candidates = []
        for person in relations.values():
            score = self._person_query_score(person, parsed)
            if score > 0:
                candidates.append((score, person))
        candidates.sort(key=lambda item: (item[0], item[1]['name']), reverse=True)
        return candidates[:5]

    def _relation_description(self, person: dict) -> list[str]:
        missing = []
        if not person['parents']:
            missing.append('Eltern')
        if not person['children']:
            missing.append('Kinder')
        if not person['spouses']:
            missing.append('Ehepartner')
        return missing

    def _siblings(self, person: dict, individuals: dict) -> list[dict]:
        if not person['parents']:
            return []
        parent_set = set(person['parents'])
        siblings = []
        for candidate in individuals.values():
            if candidate['xref'] == person['xref']:
                continue
            if parent_set & set(candidate['parents']):
                siblings.append(candidate)
        return siblings

    def _person_line(self, person: dict) -> str:
        birth = f" ({person['birth']})" if person['birth'] else ''
        return f"{self._display_name(person['name'])}{birth}"

    def _spouse_lines(self, person: dict, individuals: dict) -> list[str]:
        spouses = []
        for spouse_xref in person['spouses']:
            if spouse_xref in individuals:
                spouses.append(self._person_line(individuals[spouse_xref]))
        return spouses

    def _name_similarity_score(self, a: str, b: str) -> int:
        if not a or not b:
            return 0
        a_tokens = [token for token in a.lower().split() if token]
        b_tokens = [token for token in b.lower().split() if token]
        score = 0
        if a.lower() == b.lower():
            score += 4
        if a_tokens and b_tokens and a_tokens[0] == b_tokens[0]:
            score += 2
        if a_tokens and b_tokens and a_tokens[-1] == b_tokens[-1]:
            score += 2
        if len(set(a_tokens) & set(b_tokens)) >= 2:
            score += 2
        return score

    def _match_quality(self, source: dict, target: dict) -> str:
        score = self._name_similarity_score(source['name'], target['name'])
        if source['birth_year'] and target['birth_year']:
            if source['birth_year'] == target['birth_year']:
                score += 3
            elif abs(int(source['birth_year']) - int(target['birth_year'])) <= 2:
                score += 1
        if source['surname'] and target['surname'] and source['surname'] == target['surname']:
            score += 1
        if source['normalized_key'] == target['normalized_key'] and source['normalized_key']:
            score += 10

        if score >= 9:
            return 'sicher'
        if score >= 6:
            return 'vermutlich'
        if score >= 3:
            return 'eventuell'
        return ''

    def _find_sibling_candidates(self, sibling: dict, targets: list[dict]) -> list[tuple[str, dict]]:
        results = []
        for target in targets:
            if sibling['normalized_key'] and sibling['normalized_key'] == target['normalized_key']:
                continue
            if sibling['surname'] and target['surname'] and sibling['surname'] != target['surname']:
                continue
            if sibling['birth_year'] and target['birth_year']:
                if abs(int(sibling['birth_year']) - int(target['birth_year'])) > 10:
                    continue
            quality = self._match_quality(sibling, target)
            if quality:
                results.append((quality, target))
        quality_order = {'sicher': 3, 'vermutlich': 2, 'eventuell': 1}
        results.sort(key=lambda item: (quality_order[item[0]], self._name_similarity_score(sibling['name'], item[1]['name'])), reverse=True)
        return results[:5]

    def _find_person_candidates(self, person: dict, targets: list[dict]) -> list[tuple[str, dict]]:
        results = []
        for target in targets:
            if person['normalized_key'] and person['normalized_key'] == target['normalized_key']:
                continue
            quality = self._match_quality(person, target)
            if quality:
                results.append((quality, target))
        quality_order = {'sicher': 3, 'vermutlich': 2, 'eventuell': 1}
        results.sort(key=lambda item: (quality_order[item[0]], self._name_similarity_score(person['name'], item[1]['name'])), reverse=True)
        return results[:5]

    def _related_key_set(self, person: dict, relations: dict, relation_names: list[str]) -> set[str]:
        keys = set()
        for relation_name in relation_names:
            for xref in person.get(relation_name, []):
                related = relations.get(xref)
                if related and related.get('normalized_key'):
                    keys.add(related['normalized_key'])
        return keys

    def _sibling_key_set(self, person: dict, relations: dict) -> set[str]:
        return {
            sibling['normalized_key']
            for sibling in self._siblings(person, relations)
            if sibling.get('normalized_key')
        }

    def _format_person_summary(self, person: dict) -> str:
        parts = [self._display_name(person['name'])]
        if person.get('birth'):
            parts.append(f"geb. {person['birth']}")
        if person.get('death'):
            parts.append(f"gest. {person['death']}")
        return ' | '.join(parts)

    def _display_name(self, name: str) -> str:
        raw = (name or '').strip()
        if '/' in raw:
            parts = [part.strip() for part in raw.split('/') if part.strip()]
            if len(parts) >= 2:
                given = parts[0]
                surname = parts[1]
                if given and surname:
                    return f"{surname} / {given}"
        return raw

    def _person_sort_key(self, person: dict) -> tuple[str, str, str]:
        surname = (person.get('surname') or '').lower()
        name = (person.get('name') or '').lower()
        birth = (person.get('birth') or '').lower()
        return (surname, name, birth)

    def _person_key_set(self, relations: dict) -> set[str]:
        return {person['normalized_key'] for person in relations.values() if person.get('normalized_key')}

    def _unique_people_by_xref(self, people: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for person in people:
            xref = person.get('xref')
            if xref and xref not in seen:
                seen.add(xref)
                unique.append(person)
        unique.sort(key=self._person_sort_key)
        return unique

    def _new_people_from_xrefs(self, xrefs: list[str], relations: dict, known_keys: set[str]) -> list[dict]:
        people = []
        for xref in xrefs:
            person = relations.get(xref)
            if person and person.get('normalized_key') and person['normalized_key'] not in known_keys:
                people.append(person)
        return self._unique_people_by_xref(people)

    def _collect_enrichment_lines(self, person: dict, own_relations: dict, other_relations: dict) -> list[str]:
        known_keys = self._person_key_set(own_relations)
        sections = []

        def add_section(label: str, people: list[dict]):
            unique_people = self._unique_people_by_xref(people)
            if unique_people:
                sections.append(f"    - {label}: {', '.join(self._person_line(p) for p in unique_people)}")

        parents = self._new_people_from_xrefs(person.get('parents', []), other_relations, known_keys)
        siblings = []
        for sibling in self._siblings(person, other_relations):
            if sibling.get('normalized_key') and sibling['normalized_key'] not in known_keys:
                siblings.append(sibling)

        spouses = self._new_people_from_xrefs(person.get('spouses', []), other_relations, known_keys)
        children = self._new_people_from_xrefs(person.get('children', []), other_relations, known_keys)

        sibling_spouses = []
        sibling_children = []
        for sibling in self._unique_people_by_xref(self._siblings(person, other_relations)):
            for spouse_xref in sibling.get('spouses', []):
                spouse = other_relations.get(spouse_xref)
                if spouse and spouse.get('normalized_key') and spouse['normalized_key'] not in known_keys:
                    sibling_spouses.append(spouse)
            for child_xref in sibling.get('children', []):
                child = other_relations.get(child_xref)
                if child and child.get('normalized_key') and child['normalized_key'] not in known_keys:
                    sibling_children.append(child)

        add_section('Eltern', parents)
        add_section('Geschwister', siblings)
        add_section('Ehepartner', spouses)
        add_section('Kinder', children)
        add_section('Geschwister-Ehepartner', sibling_spouses)
        add_section('Kinder der Geschwister', sibling_children)

        return sections

    def _lineage_enrichment_report(self, file_ids: list[int]) -> str:
        if len(file_ids) < 2:
            return 'Bitte mindestens zwei GEDCOM-Dateien auswählen, um den Vergleich zu starten.'

        file_records = {file_id: self.file_summary(file_id) for file_id in file_ids}
        relations_by_file = {file_id: self.build_family_relations(file_id) for file_id in file_ids}
        file_keys = {
            file_id: {person['normalized_key']: person for person in relations.values() if person.get('normalized_key')}
            for file_id, relations in relations_by_file.items()
        }

        output = ['Abgleich der Personen mit potenziellen Ergänzungen aus anderen GEDCOM-Dateien:', '']
        found_any = False

        for file_id in file_ids:
            own_name = file_records[file_id]['name']
            own_relations = relations_by_file[file_id]
            other_file_ids = [fid for fid in file_ids if fid != file_id]

            person_blocks = []
            for person in sorted(own_relations.values(), key=self._person_sort_key):
                person_sections = []

                for other_file_id in other_file_ids:
                    other_relations = relations_by_file[other_file_id]
                    other_keys = file_keys[other_file_id]

                    direct_match = other_keys.get(person['normalized_key'])
                    if direct_match:
                        matched_person = direct_match
                    else:
                        candidates = self._find_person_candidates(person, list(other_relations.values()))
                        if not candidates:
                            continue
                        quality, matched_person = candidates[0]
                        if quality == 'eventuell':
                            continue

                    additions = self._collect_enrichment_lines(matched_person, own_relations, other_relations)
                    if additions:
                        person_sections.append((file_records[other_file_id]['name'], additions))

                if person_sections:
                    person_blocks.append((person, person_sections))

            if person_blocks:
                found_any = True
                output.append(f"Datei: {own_name}")
                for person, person_sections in sorted(person_blocks, key=lambda item: self._person_sort_key(item[0])):
                    output.append(f"**{self._format_person_summary(person)}**")
                    for other_name, additions in person_sections:
                        output.append(f"  Ergänzungen aus {other_name}:")
                        output.extend(additions)
                    output.append('')
                output.append('')

        if not found_any:
            return 'Es wurden keine Personen gefunden, bei denen sich aus den anderen GEDCOM-Dateien zusätzliche Linien ableiten lassen.'

        return '\n'.join(output).rstrip()

    def _spouse_hits_for_siblings(self, file_ids: list[int]) -> str:
        if len(file_ids) < 2:
            return 'Bitte mindestens zwei GEDCOM-Dateien auswählen, um den Vergleich zu starten.'

        file_records = {file_id: self.file_summary(file_id) for file_id in file_ids}
        relations_by_file = {file_id: self.build_family_relations(file_id) for file_id in file_ids}
        file_keys = {file_id: {person['normalized_key']: person for person in relations.values()} for file_id, relations in relations_by_file.items()}
        common_keys = set.intersection(*(set(keys) for keys in file_keys.values()))

        output = []
        if not common_keys:
            output.append('Es wurden keine gemeinsamen Personen gefunden, anhand derer die Geschwister-Ehepartner verglichen werden könnten.')
            return '\n'.join(output)

        output.append('Ehepartner der Geschwister für gemeinsame Personen:')
        output.append('')

        for key in common_keys:
            primary = file_keys[file_ids[0]][key]
            secondary = file_keys[file_ids[1]][key]
            output.append(f"Gemeinsame Person: {primary['name']} ({primary['birth']})")
            for file_id, own_person, other_file_id in [(file_ids[0], primary, file_ids[1]), (file_ids[1], secondary, file_ids[0])]:
                own_name = file_records[file_id]['name']
                other_name = file_records[other_file_id]['name']
                output.append(f"  In Datei {own_name} gefundene Geschwister und ihre möglichen Ehepartner aus {other_name}:")
                siblings = self._siblings(own_person, relations_by_file[file_id])
                if not siblings:
                    output.append('    - Keine Geschwisterdaten im eigenen Stammbaum.')
                    continue
                for sibling in siblings:
                    sibling_line = self._person_line(sibling)
                    output.append(f"    - Geschwister: {sibling_line}")
                    direct_match = file_keys[other_file_id].get(sibling['normalized_key'])
                    if direct_match:
                        spouse_lines = self._spouse_lines(direct_match, relations_by_file[other_file_id])
                        if spouse_lines:
                            output.append(f"      * Direkter Treffer in {other_name}: {', '.join(spouse_lines)}")
                        else:
                            output.append(f"      * Direkter Treffer in {other_name}, aber keine Ehepartnerdaten vorhanden.")
                    else:
                        candidates = self._find_sibling_candidates(sibling, list(relations_by_file[other_file_id].values()))
                        spouse_found = False
                        for quality, candidate in candidates:
                            spouse_lines = self._spouse_lines(candidate, relations_by_file[other_file_id])
                            if spouse_lines:
                                spouse_found = True
                                candidate_line = self._person_line(candidate)
                                output.append(f"      * {quality}: {candidate_line} → Ehepartner: {', '.join(spouse_lines)}")
                        if not spouse_found:
                            output.append(f"      * Keine passenden Ehepartner-Treffer für diesen Geschwisterkandidaten in {other_name}.")
            output.append('')
        return '\n'.join(output)

    def compare_files(self, file_ids: list[int]) -> str:
        return self._lineage_enrichment_report(file_ids)


class GedcomApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('GEDCOM-Übersicht und Vergleich')
        self.geometry('900x650')
        self.db = GedcomDatabase(DB_FILE)
        self.create_widgets()
        self.refresh_file_list()

    def create_widgets(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill='x', padx=8, pady=8)

        self.import_button = ttk.Button(toolbar, text='GEDCOM importieren', command=self.import_gedcom)
        self.import_button.pack(side='left')

        self.import_pdf_button = ttk.Button(toolbar, text='PDF importieren', command=self.import_pdf)
        self.import_pdf_button.pack(side='left', padx=6)

        self.compare_button = ttk.Button(toolbar, text='Vergleich starten', command=self.compare_selected)
        self.compare_button.pack(side='left', padx=6)

        self.sibling_spouse_button = ttk.Button(toolbar, text='Ehepartner der Geschwister', command=self.compare_sibling_spouses)
        self.sibling_spouse_button.pack(side='left', padx=6)

        self.tree_button = ttk.Button(toolbar, text='Stammbaum anzeigen', command=self.show_family_tree)
        self.tree_button.pack(side='left', padx=6)

        self.person_search_label = ttk.Label(toolbar, text='Person (Name; Geburts-/Sterbedatum):')
        self.person_search_label.pack(side='left', padx=10)

        self.person_search_var = tk.StringVar()
        self.person_search_entry = ttk.Entry(toolbar, width=30, textvariable=self.person_search_var)
        self.person_search_entry.pack(side='left')

        self.person_search_button = ttk.Button(toolbar, text='Geschwister-Ehepartner für Person', command=self.compare_sibling_spouses_for_person)
        self.person_search_button.pack(side='left', padx=6)

        self.clear_button = ttk.Button(toolbar, text='Datenbank aktualisieren', command=self.refresh_file_list)
        self.clear_button.pack(side='left')

        list_frame = ttk.LabelFrame(self, text='Geladene GEDCOM-Dateien')
        list_frame.pack(fill='both', expand=False, padx=8, pady=4)

        self.file_tree = ttk.Treeview(list_frame, columns=('name', 'imported', 'persons', 'families'), show='headings', selectmode='extended', height=8)
        self.file_tree.heading('name', text='Datei')
        self.file_tree.heading('imported', text='Importiert am')
        self.file_tree.heading('persons', text='Personen')
        self.file_tree.heading('families', text='Familien')
        self.file_tree.column('name', width=330)
        self.file_tree.column('imported', width=180)
        self.file_tree.column('persons', width=90, anchor='center')
        self.file_tree.column('families', width=90, anchor='center')
        self.file_tree.pack(fill='x', padx=4, pady=4)

        pdf_frame = ttk.LabelFrame(self, text='PDF-Datenbrowser')
        pdf_frame.pack(fill='both', expand=False, padx=8, pady=4)

        pdf_controls = ttk.Frame(pdf_frame)
        pdf_controls.pack(fill='x', padx=4, pady=4)

        ttk.Label(pdf_controls, text='PDF:').pack(side='left')
        self.pdf_file_var = tk.StringVar()
        self.pdf_files_map: dict[str, int] = {}
        self.pdf_file_combo = ttk.Combobox(pdf_controls, width=42, textvariable=self.pdf_file_var, state='readonly')
        self.pdf_file_combo.pack(side='left', padx=6)
        self.pdf_file_combo.bind('<<ComboboxSelected>>', lambda event: self.load_pdf_records())

        ttk.Label(pdf_controls, text='Suche:').pack(side='left', padx=(12, 0))
        self.pdf_search_var = tk.StringVar()
        self.pdf_search_entry = ttk.Entry(pdf_controls, width=24, textvariable=self.pdf_search_var)
        self.pdf_search_entry.pack(side='left', padx=6)
        self.pdf_search_entry.bind('<Return>', lambda event: self.load_pdf_records())

        ttk.Label(pdf_controls, text='Nachname:').pack(side='left', padx=(12, 0))
        self.pdf_surname_var = tk.StringVar()
        self.pdf_surname_entry = ttk.Entry(pdf_controls, width=16, textvariable=self.pdf_surname_var)
        self.pdf_surname_entry.pack(side='left', padx=6)
        self.pdf_surname_entry.bind('<Return>', lambda event: self.load_pdf_records())

        ttk.Label(pdf_controls, text='Vorname:').pack(side='left', padx=(12, 0))
        self.pdf_given_var = tk.StringVar()
        self.pdf_given_entry = ttk.Entry(pdf_controls, width=16, textvariable=self.pdf_given_var)
        self.pdf_given_entry.pack(side='left', padx=6)
        self.pdf_given_entry.bind('<Return>', lambda event: self.load_pdf_records())

        self.pdf_filter_button = ttk.Button(pdf_controls, text='Filtern', command=self.load_pdf_records)
        self.pdf_filter_button.pack(side='left', padx=6)

        self.pdf_clear_button = ttk.Button(pdf_controls, text='Filter zurücksetzen', command=self.clear_pdf_filters)
        self.pdf_clear_button.pack(side='left', padx=6)

        self.pdf_info_var = tk.StringVar(value='Keine PDF ausgewählt.')
        self.pdf_info_label = ttk.Label(pdf_frame, textvariable=self.pdf_info_var)
        self.pdf_info_label.pack(fill='x', padx=4)

        pdf_table_frame = ttk.Frame(pdf_frame)
        pdf_table_frame.pack(fill='both', expand=True, padx=4, pady=4)

        pdf_scrollbar = ttk.Scrollbar(pdf_table_frame, orient='vertical')
        pdf_scrollbar.pack(side='right', fill='y')

        self.pdf_tree = ttk.Treeview(
            pdf_table_frame,
            columns=('page', 'block', 'name', 'age', 'origin', 'destination', 'year', 'occupation', 'source', 'remarks', 'summary'),
            show='headings',
            height=8,
            yscrollcommand=pdf_scrollbar.set,
        )
        self.pdf_tree.heading('page', text='Seite')
        self.pdf_tree.heading('block', text='Block')
        self.pdf_tree.heading('name', text='Name')
        self.pdf_tree.heading('age', text='Alter/Geb. Datum')
        self.pdf_tree.heading('origin', text='Herkunft')
        self.pdf_tree.heading('destination', text='Ziel')
        self.pdf_tree.heading('year', text='Jahr')
        self.pdf_tree.heading('occupation', text='Beruf')
        self.pdf_tree.heading('source', text='Quelle')
        self.pdf_tree.heading('remarks', text='Bemerkungen')
        self.pdf_tree.heading('summary', text='Zusammenfassung')
        self.pdf_tree.column('page', width=60, anchor='center')
        self.pdf_tree.column('block', width=60, anchor='center')
        self.pdf_tree.column('name', width=220)
        self.pdf_tree.column('age', width=130)
        self.pdf_tree.column('origin', width=150)
        self.pdf_tree.column('destination', width=160)
        self.pdf_tree.column('year', width=70, anchor='center')
        self.pdf_tree.column('occupation', width=130)
        self.pdf_tree.column('source', width=220)
        self.pdf_tree.column('remarks', width=220)
        self.pdf_tree.column('summary', width=520)
        self.pdf_tree.pack(side='left', fill='both', expand=True)
        pdf_scrollbar.config(command=self.pdf_tree.yview)

        result_frame = ttk.LabelFrame(self, text='Vergleichsergebnis')
        result_frame.pack(fill='both', expand=True, padx=8, pady=8)

        result_inner = ttk.Frame(result_frame)
        result_inner.pack(fill='both', expand=True, padx=4, pady=4)

        result_scrollbar = ttk.Scrollbar(result_inner, orient='vertical')
        result_scrollbar.pack(side='right', fill='y')

        self.result_text = tk.Text(result_inner, wrap='word', state='disabled', yscrollcommand=result_scrollbar.set)
        self.result_text.pack(side='left', fill='both', expand=True)
        result_scrollbar.config(command=self.result_text.yview)

        self.refresh_pdf_file_list()

    def import_gedcom(self):
        paths = filedialog.askopenfilenames(title='GEDCOM-Dateien auswählen', filetypes=[('GEDCOM Dateien', '*.ged *.gedcom'), ('Alle Dateien', '*.*')])
        if not paths:
            return

        imported = []
        errors = []
        for path in paths:
            try:
                file_id = self.db.import_file(path)
                imported.append(path)
            except Exception as exc:
                errors.append(f'{os.path.basename(path)}: {exc}')

        self.refresh_file_list()
        if imported:
            messagebox.showinfo('Import abgeschlossen', f'{len(imported)} GEDCOM-Datei(en) importiert.')
        if errors:
            messagebox.showerror('Importfehler', '\n'.join(errors))

    def import_pdf(self):
        path = filedialog.askopenfilename(title='PDF-Datei auswählen', filetypes=[('PDF Dateien', '*.pdf'), ('Alle Dateien', '*.*')])
        if not path:
            return
        try:
            result = self.db.import_pdf(path)
        except Exception as exc:
            messagebox.showerror('PDF-Importfehler', f"{os.path.basename(path)}: {exc}")
            return

        report = [
            'PDF-Import abgeschlossen',
            '',
            f"Datei: {result['file_name']}",
            f"Seiten: {result['pages']}",
            f"Zeilen: {result['lines']}",
            f"als Personen erkannt: {result['persons']}",
            '',
            'Hinweis:',
            'Die Daten wurden strukturiert in den Tabellen `pdf_files`, `pdf_pages` und `pdf_records` abgelegt.',
        ]
        self.set_result_text('\n'.join(report))
        self.refresh_pdf_file_list(select_file_id=result['file_id'])
        messagebox.showinfo('PDF-Import abgeschlossen', f"{result['file_name']} wurde importiert.")

    def refresh_pdf_file_list(self, select_file_id: int | None = None):
        rows = self.db.list_pdf_files()
        self.pdf_files_map = {}
        values = []
        selected_name = ''
        for row in rows:
            display = f"{row['name']} ({row['imported_at']})"
            self.pdf_files_map[display] = row['id']
            values.append(display)
            if select_file_id is not None and row['id'] == select_file_id:
                selected_name = display
        self.pdf_file_combo['values'] = values
        if selected_name:
            self.pdf_file_var.set(selected_name)
        elif values and not self.pdf_file_var.get():
            self.pdf_file_var.set(values[0])
        elif self.pdf_file_var.get() not in self.pdf_files_map and values:
            self.pdf_file_var.set(values[0])
        self.load_pdf_records()

    def _selected_pdf_file_id(self) -> int | None:
        selected = self.pdf_file_var.get().strip()
        return self.pdf_files_map.get(selected)

    def clear_pdf_filters(self):
        self.pdf_search_var.set('')
        self.pdf_surname_var.set('')
        self.pdf_given_var.set('')
        self.load_pdf_records()

    def load_pdf_records(self):
        for item in self.pdf_tree.get_children():
            self.pdf_tree.delete(item)

        file_id = self._selected_pdf_file_id()
        if not file_id:
            self.pdf_info_var.set('Keine PDF ausgewählt.')
            return

        search = self.pdf_search_var.get().strip()
        surname = self.pdf_surname_var.get().strip()
        given = self.pdf_given_var.get().strip()
        rows = self.db.get_pdf_records(file_id, query=search, surname=surname, given=given)
        summary = self.db.get_pdf_file_summary(file_id)
        self.pdf_info_var.set(
            f"{summary['name']}: {summary['pages']} Seiten, {summary['records']} Datensätze, {summary['persons']} erkannte Personen | Treffer: {len(rows)}"
        )

        for row in rows:
            self.pdf_tree.insert(
                '',
                'end',
                values=(
                    row['page_no'],
                    row['block_no'],
                    row['display_name'] or row['raw_text'][:60],
                    row['age_or_birth'] or row['birth'],
                    row['origin'] or row['residence'],
                    row['destination'] or row['emigration_place'],
                    row['emigration_date'],
                    row['occupation'],
                    row['source'],
                    row['remarks'],
                    row['summary'] or row['raw_text'],
                ),
            )

    def refresh_file_list(self):
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        for row in self.db.list_files():
            summary = self.db.file_summary(row['id'])
            self.file_tree.insert('', 'end', iid=row['id'], values=(summary['name'], row['imported_at'], summary['individuals'], summary['families']))

    def compare_selected(self):
        selected = self.file_tree.selection()
        if len(selected) < 2:
            messagebox.showwarning('Auswahl erforderlich', 'Bitte mindestens zwei GEDCOM-Dateien auswählen.')
            return
        file_ids = [int(item) for item in selected]
        result = self.db.compare_files(file_ids)
        self.set_result_text(result)

    def compare_sibling_spouses(self):
        selected = self.file_tree.selection()
        if len(selected) < 2:
            messagebox.showwarning('Auswahl erforderlich', 'Bitte mindestens zwei GEDCOM-Dateien auswählen.')
            return
        file_ids = [int(item) for item in selected]
        result = self.db._spouse_hits_for_siblings(file_ids)
        self.set_result_text(result)

    def compare_sibling_spouses_for_person(self):
        selected = self.file_tree.selection()
        if len(selected) < 2:
            messagebox.showwarning('Auswahl erforderlich', 'Bitte mindestens zwei GEDCOM-Dateien auswählen.')
            return
        query = self.person_search_var.get().strip()
        if not query:
            messagebox.showwarning('Suche erforderlich', 'Bitte den Namen und das Geburtsjahr der Person eingeben.')
            return

        file_ids = [int(item) for item in selected]
        persons = []
        relations_by_file = {}
        for file_id in file_ids:
            relations = self.db.build_family_relations(file_id)
            relations_by_file[file_id] = relations
            matches = self.db._find_person_matches(relations, query)
            if matches:
                persons.append((file_id, matches[0][1]))
            else:
                persons.append((file_id, None))

        if any(found is None for _, found in persons):
            missing = [self.db.file_summary(fid)['name'] for fid, person in persons if person is None]
            messagebox.showinfo('Person nicht gefunden', f"Die Person konnte in folgenden Dateien nicht gefunden werden: {', '.join(missing)}")
            return

        result = self._sibling_spouse_report_for_persons(persons, relations_by_file)
        self.set_result_text(result)

    def _sibling_spouse_report_for_persons(self, persons: list[tuple[int, dict]], relations_by_file: dict) -> str:
        if len(persons) < 2:
            return 'Bitte mindestens zwei GEDCOM-Dateien auswählen.'

        output = ['Ehepartner der Geschwister für die gesuchte Person:','']
        main_person = persons[0][1]
        output.append(f"Gesuchte Person: {main_person['name']} ({main_person['birth']})")
        output.append('')

        for file_id, person in persons:
            other_file_ids = [fid for fid, _ in persons if fid != file_id]
            own_name = self.db.file_summary(file_id)['name']
            output.append(f"In Datei {own_name}:")
            siblings = self._siblings(person, relations_by_file[file_id])
            if not siblings:
                output.append('  - Keine Geschwisterdaten im eigenen Stammbaum.')
                output.append('')
                continue
            for sibling in siblings:
                sibling_line = self._person_line(sibling)
                output.append(f"  - Geschwister: {sibling_line}")
                for other_file_id in other_file_ids:
                    other_name = self.db.file_summary(other_file_id)['name']
                    direct_match = self._find_direct_sibling_match(sibling, relations_by_file[other_file_id])
                    if direct_match:
                        spouse_lines = self._spouse_lines(direct_match, relations_by_file[other_file_id])
                        if spouse_lines:
                            output.append(f"      * Direkter Treffer in {other_name}: Ehepartner: {', '.join(spouse_lines)}")
                        else:
                            output.append(f"      * Direkter Treffer in {other_name}, aber keine Ehepartnerdaten vorhanden.")
                    else:
                        candidates = self._find_sibling_candidates(sibling, list(relations_by_file[other_file_id].values()))
                        if candidates:
                            for quality, candidate in candidates:
                                spouse_lines = self._spouse_lines(candidate, relations_by_file[other_file_id])
                                if spouse_lines:
                                    candidate_line = self._person_line(candidate)
                                    output.append(f"      * {quality}: {candidate_line} → Ehepartner: {', '.join(spouse_lines)}")
                        else:
                            output.append(f"      * Keine potenziellen Entsprechungen in {other_name} gefunden.")
            output.append('')
        return '\n'.join(output)

    def _find_direct_sibling_match(self, sibling: dict, relations: dict) -> dict | None:
        return relations.get(sibling['normalized_key'])

    def show_family_tree(self):
        selected = self.file_tree.selection()
        if len(selected) != 1:
            messagebox.showwarning('Auswahl erforderlich', 'Bitte genau eine GEDCOM-Datei auswählen, um den Stammbaum anzuzeigen.')
            return
        file_id = int(selected[0])
        relations = self.db.build_family_relations(file_id)
        summary = self.db.file_summary(file_id)
        if not relations:
            messagebox.showinfo('Keine Daten', 'Für die ausgewählte GEDCOM-Datei sind keine Personen- oder Familiendaten vorhanden.')
            return
        self.open_family_tree_window(relations, summary['name'])

    def open_family_tree_window(self, relations: dict, title: str):
        window = tk.Toplevel(self)
        window.title(f'Stammbaum: {title}')
        frame = ttk.Frame(window)
        frame.pack(fill='both', expand=True)

        canvas = tk.Canvas(frame, bg='white')
        hbar = ttk.Scrollbar(frame, orient='horizontal', command=canvas.xview)
        vbar = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        hbar.pack(side='bottom', fill='x')
        vbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        nodes_by_gen, positions = self._layout_family_tree(relations)
        self._draw_family_tree(canvas, relations, nodes_by_gen, positions)

        width = max(x for x, y in positions.values()) + 200
        height = max(y for x, y in positions.values()) + 150
        canvas.configure(scrollregion=(0, 0, width, height))

    def _layout_family_tree(self, relations: dict) -> tuple[dict[int, list[str]], dict[str, tuple[int, int]]]:
        from collections import deque

        roots = [xref for xref, person in relations.items() if not person['parents']]
        if not roots:
            roots = sorted(relations.keys(), key=lambda x: len(relations[x]['parents']))[:3]

        generation = {}
        queue = deque((xref, 0) for xref in roots)
        while queue:
            xref, gen = queue.popleft()
            if xref in generation and generation[xref] <= gen:
                continue
            generation[xref] = gen
            for child in relations[xref]['children']:
                queue.append((child, gen + 1))

        for xref, person in relations.items():
            if xref not in generation:
                if person['parents']:
                    parent_gens = [generation.get(parent, 0) for parent in person['parents']]
                    generation[xref] = min(parent_gens) + 1 if parent_gens else 0
                else:
                    generation[xref] = 0

        groups = {}
        for xref, gen in generation.items():
            groups.setdefault(gen, []).append(xref)

        positions = {}
        for gen, xrefs in sorted(groups.items()):
            width = 180
            height = 120
            total = len(xrefs)
            for idx, xref in enumerate(sorted(xrefs, key=lambda x: relations[x]['name'])):
                x = 100 + idx * (width + 40)
                y = 50 + gen * (height + 60)
                positions[xref] = (x, y)

        return groups, positions

    def _draw_family_tree(self, canvas: tk.Canvas, relations: dict, groups: dict[int, list[str]], positions: dict[str, tuple[int, int]]):
        for xref, person in relations.items():
            x, y = positions[xref]
            for child_xref in person['children']:
                if child_xref in positions:
                    cx, cy = positions[child_xref]
                    canvas.create_line(x + 80, y + 40, cx + 80, cy, arrow='last')

        for xref, person in relations.items():
            x, y = positions[xref]
            canvas.create_rectangle(x, y, x + 160, y + 50, fill='#d0e6ff', outline='#2a5caa')
            canvas.create_text(x + 80, y + 18, text=person['name'], font=('Arial', 10, 'bold'))
            birth = person['birth'] if person['birth'] else 'geb. ?'
            canvas.create_text(x + 80, y + 34, text=birth, font=('Arial', 9))

    def set_result_text(self, text: str):
        self.result_text.configure(state='normal')
        self.result_text.delete('1.0', tk.END)
        self.result_text.tag_configure('bold', font=('TkDefaultFont', 9, 'bold'))
        for line in text.splitlines():
            if line.strip().startswith('**') and line.strip().endswith('**') and line.strip().count('**') == 2:
                prefix = line[:len(line) - len(line.lstrip())]
                content = line.strip()[2:-2]
                if prefix:
                    self.result_text.insert(tk.END, prefix)
                self.result_text.insert(tk.END, content + '\n', 'bold')
            else:
                self.result_text.insert(tk.END, line + '\n')
        self.result_text.configure(state='disabled')


if __name__ == '__main__':
    app = GedcomApp()
    app.mainloop()
