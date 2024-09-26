"""fghjkkl"""
from datetime import datetime
import random
import re
import textwrap
import stanza
# import PyPDF2
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from docx import Document
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# Завантаження та ініціалізація українського NLP-пайплайна
stanza.download('uk')
nlp = stanza.Pipeline('uk')
OZN_OSOB = ['1 одн', '2 одн', '1 мн', '2 мн'] #перелік осіб, котрі значать означено-особове речення
# вони -- неозн.особове
# прислів'я -- узаг.особове
# присудок не дієслово -- безособове

# фіксуємо шляхи до наших файлів з поділеними типами
type_to_file = {'Просте':'typed_sentanses\\proste.txt', 'Односкладне':'typed_sentanses\\odnoscladne.txt', 'Означено-особове':'typed_sentanses\\oznacheno-osobove.txt', \
                    'Неозначено-особове':'typed_sentanses\\neoznacheno-osobove.txt', 'Узагальнено-особове':'typed_sentanses\\yzahalneno-osobove.txt', \
                    'Безособове':'typed_sentanses\\bezosobove.txt', 'Двоскладне':'typed_sentanses\\dvoskladne.txt', 'Називне':'typed_sentanses\\nazyvne.txt', 'Складносурядне':'typed_sentanses\\skladnosyriadne.txt', \
                    'Складнопідрядне':'typed_sentanses\\skladnopidriadne.txt', 'Складне':'typed_sentanses\\skladne.txt', 'Складне безсполучникове':'typed_sentanses\\skladne_bezspolychnukove.txt'}

# просто перелік усіх можливих типів речень, які визначає ця програма
all_types = ['Просте', 'Односкладне', 'Означено-особове', 'Неозначено-особове', 'Узагальнено-особове', \
              'Безособове', 'Двоскладне', 'Називне', 'Складносурядне', 'Складнопідрядне', 'Складне', 'Складне безсполучникове']
# створюємо словник, щоб розуміти скільки яких речень маємо
count_dictionary = dict.fromkeys(all_types, 0)

# Клас речення
class Sentence:
    """Клас Речення
    : речення поділене
    : саме речення (текст)
    : roots - ліст усіх підметів чи присудків
    : sentence_consist - тут є к-ть підметів, присудків, а також сполучників
    : тип речення"""
    def __init__(self, sentence):
        self.sentence = sentence
        self.text_sent = sentence.text
        self.roots = []
        self.sentence_consist = {"numb_subject":0, "numb_predicate":0, "cconj":0, "sconj":0}
        for word in self.sentence.words:
            if word.deprel == 'root':
                self.roots.append(word)
            elif word.deprel == 'nsubj':
                self.sentence_consist['numb_predicate'] += 1
            elif word.upos == 'cconj':
                self.sentence_consist['cconj'] += 1
            elif word.upos == 'sconj':
                self.sentence_consist['sconj'] += 1
        self.sentence_consist['numb_subject'] = len(self.roots)
        self.sentence_type = []
        self.current_clause = []

    def determine_sentence_type_2(self):
        """Визначаємо тип речення
        приклад результату 
        (Просте, Двооскладне, Називне)
        ('Просте', 'Односкладне', 'Означено-особове')
        ('Просте', 'Односкладне', 'Неозначено-особове')
        ('Просте', 'Односкладне', 'Узагальнено-особове')
        ('Просте', 'Односкладне', 'Безособове')
        ('Двоскладне', 'Називне')

        ('Складне', 'Складносурядне')
        ('Складне', 'Складнопідрядне')
        ('Складне', 'Складне безсполучникове')
        """
        if self.sentence_consist['numb_subject'] < 2 and self.sentence_consist['numb_predicate'] < 2 and \
            not self.sentence_consist["cconj"] and not self.sentence_consist["sconj"]:
            # тобто маємо по 1 граматичній основі -- просте речення
            # ПЕРЕВІРЯТИ ЧИ ВОНИ Є ОКРЕМИМ ГРАМ.ОСНОВАМИ, ТИПУ ЧИ ЦЕ НЕ 1 З 1ГО 2ГЕ З 2ГОГО
            # наче тепер нема сполучників підрядносі/сурядності, то все круто
            self.sentence_type.append('Просте')
            if self.sentence_consist['numb_subject'] and self.sentence_consist['numb_predicate']:
                self.sentence_type.extend(['Двоскладне', 'Називне', ''])
            else:
                self.sentence_type.append('Односкладне')
                our_predicate = Predicate(self.roots[0])
                if our_predicate.part_of_speech != 'VERB':
                    self.sentence_type.append('Безособове')
                else:
                    our_predicate.find_face()
                    if our_predicate.face in OZN_OSOB:
                        self.sentence_type.append('Означено-особове')
                    elif our_predicate.face == '3 мн':
                        self.sentence_type.append('Неозначено-особове')
                    else:
                        self.sentence_type.append('Узагальнено-особове')
        else:
            self.sentence_type.append('Складне')
            if self.sentence_consist["cconj"]:
                self.sentence_type.append('Складносурядне')
            elif self.sentence_consist["sconj"]:
                self.sentence_type.append('Складнопідрідне')
            else:
                self.sentence_type.append('Складне безсполучникове')
            self.sentence_type.append('')
        for el in self.sentence_type:
            if el != '':
                count_dictionary[el] += 1
        self.sentence_type = tuple(self.sentence_type)

class Predicate:
    """Клас Присудка
    : саме слово
    : частина мови (всі, крім дієсл - безособове речення)
    : особовість присудка
    """
    def __init__(self, word = '', face=''):
        self.word = word
        self.part_of_speech = self.word.upos
        self.face = face

    def find_face(self):
        """Визначаємо особу присудка, щоб надати тип реченню"""
        if self.part_of_speech == 'VERB':
            # Визначення особи та числа
            if 'Person=1' in self.word.feats:
                if 'Number=Sing' in self.word.feats:
                    self.face = '1 одн'
                    # print("Це дієслово вказує на першу особу однини (я).")
                elif 'Number=Plur' in self.word.feats:
                    self.face = '1 мн'
                    # print("Це дієслово вказує на першу особу множини (ми).")
            elif 'Person=2' in self.word.feats:
                if 'Number=Sing' in self.word.feats:
                    self.face = '2 одн'
                    # print("Це дієслово вказує на другу особу однини (ти).")
                elif 'Number=Plur' in self.word.feats:
                    self.face = '2 мн'
                    # print("Це дієслово вказує на другу особу множини (ви).")
            elif 'Person=3' in self.word.feats:
                if 'Number=Sing' in self.word.feats:
                    self.face = '3 одн'
                    # print("Це дієслово вказує на третю особу однини (він/вона/воно).")
                elif 'Number=Plur' in self.word.feats:
                    self.face = '3 мн'
                    # print("Це дієслово вказує на третю особу множини (вони).")


# Основна функція
def main(file_path, statistic=False, new_file_path=False):
    """приймаємо шлях файлу і бажаний тип речення, а також чи хочемо ми зчитати звідкись додаткові дані"""
    text = read_pdf_file(file_path)
    doc = nlp(text)
    sorted_sentences = sort_sentences_by_type(doc)
    if statistic:
        # Виведення кількості речень за типом, якщо хочемо перевітити чи все окей
        for sentence_type, sentences in sorted_sentences.items():
            print(f'Граматичний тип: {sentence_type}, Кількість речень: {len(sentences)}')
    if new_file_path:
        # створить новий словник речень і позаписує речення за типами у файли
        get_sentense_type_write_to_doc(sorted_sentences)

def read_pdf_file(file_path):
    """Зчитуємо дані з docx, робимо їх придатними для роботи"""
    doc = Document(file_path)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text

def sort_sentences_by_type(doc):
    """Функція, яка з отриманого тексту для, кожне речення робить екземпляром класу речення, 
    і запускає для них визначення типу в цей час, сортує речення за типами, а також відстортовує
    занадто короткі чи ті, які були неправильно записані(не містять . в кінці)"""
    pattern = r'^[a-zа-я]'
    sentence_groups = {}
    for sentence in doc.sentences:
        if len(sentence.text) < 45 or re.match(pattern, sentence.text) or not sentence.text.strip().endswith('.'):
            continue
        sentence = Sentence(sentence)
        sentence.determine_sentence_type_2()
        if sentence.sentence_type not in sentence_groups:
            sentence_groups[sentence.sentence_type] = []
        sentence_groups[sentence.sentence_type].append(sentence)
    print(sentence_groups)
    return sentence_groups

def get_sentense_type_write_to_doc(sorted_sentences):
    """Маючи всі речення, записуємо всі по типізованих доках"""
    file_handles = {}
    for key, filename in type_to_file.items():
        file_handles[key] = open(filename, 'a', encoding='utf-8')  # Відкриваємо файл для дозапису

    # Проходимо по кожному реченню і записуємо його у відповідні файли
    for tuple_sent_key, sentanse_list in sorted_sentences.items():
        for sentence_type in tuple_sent_key:
            if sentence_type in file_handles:
                timed = []
                for el in sentanse_list:
                    timed.append(el.text_sent)
                timed = '\n'.join(timed)
                file_handles[sentence_type].write(timed)
    for file in file_handles.values():
        file.close()

    print("Речення записані у відповідні файли.")

# def get_sentense_by_type(sorted_sentences, selected_type, number=1):
#     """Маючи всі речення, шуканий тип і кількість, поверитаємо речення"""
#     result = []
#     ind = (0 if selected_type in ['Просте', 'Складне'] else 1 if selected_type in ['Двооскладне', 'Односкладне'] else 2)
#     # if selected_type in [sorted_sentences]:
#     print(f'Речення типу {selected_type}:')
#     for list_sent_type, list_sent in sorted_sentences.items():
#         if len(list_sent_type) >= ind and list_sent_type[ind] == selected_type:
#             print(f'  {list_sent}')
#             result.extend(list_sent)
#     return result
    # else:
    #     print(f'Речень типу {selected_type} не знайдено.')

def exersize_mixed_sentances(type_of_correct_answer, num_of_options=4):
    """За типом правильно відповіді вибираємо наш тест
    Автоматично маємо 4 варіанти відповіді, але можна змінити на більше
    Повертає значення правильної відповіді"""
    result = []
    numb_of_correct_answer = random.randint(0, num_of_options-1)

    devided_by_mix = [['Просте', 'Складне'],
    ['Односкладне', 'Двоскладне'],
    ['Означено-особове', 'Неозначено-особове', 'Узагальнено-особове','Безособове'],
    ['Називне', 'Складносурядне', 'Складнопідрядне', 'Складне безсполучникове']]

    this_part = [el for el in devided_by_mix if type_of_correct_answer in el][0]
    if sum([count_dictionary[el] for el in this_part if el != type_of_correct_answer]) < num_of_options - 1:
        return f'У вашому тексті недостатньо речень інших типів, аби створити тест з одною правильною відповіддю - {type_of_correct_answer} речення'
    rozpodil = generate_random_sum_with_individual_limits(len(this_part)-1, num_of_options-1, [count_dictionary[el] for el in this_part if el != type_of_correct_answer])
    #-1, бо правильна тільки 1, правильній відповіді даєм значення 1
    numb_dict = {}
    for ell in this_part:
        if ell != type_of_correct_answer:
            numb_dict[type_to_file[ell]] = rozpodil.pop(0)
    result = [get_random_sentences_from_file(key, values) for key, values in numb_dict.items()]
    try:
        result.insert(numb_of_correct_answer, get_random_sentences_from_file(type_to_file[type_of_correct_answer], 1)[0])
    except IndexError:
        print("У цьому документі нема речень, обраного Вами типу")
        return
    
    resultt = [str(item) for sublist in result for item in (sublist if isinstance(sublist, list) else [sublist])]
    letters_for_answers = ['А', 'Б', 'В', 'Г', 'Ґ']
    resultt = [letters_for_answers[i] + ') ' + el for i, el in enumerate(resultt)]
    zavdannia = f'Серед запропонованих варіантів відповідей, знайдіть ОДНЕ {type_of_correct_answer} речення'
    resultt.insert(0, zavdannia)
    # resultt = '\n'.join(resultt)
    print(resultt)
    return resultt, letters_for_answers[numb_of_correct_answer]

def get_list_of_exersize(list_of_tasks, numb_of_options=4):
    """Отримує ліст типів речень і кількість відповідей, повертає список списків 
    і окремий список правильних відповідей"""
    result = []
    answers = []
    for el in list_of_tasks:
        if isinstance(el, list):
            if len(list_of_tasks) != 1:
                continue
            else:
                return el
        task, corr = exersize_mixed_sentances(el, numb_of_options)
        result.append(task)
        answers.append(corr)
    return result, answers

# def generate_random_sum(n, total):
#     """Генерує n випадкових чисел, що в сумі дають total"""
#     # Створюємо n-1 випадкових точок поділу в діапазоні [0, total]
#     cuts = sorted([random.randint(0, total) for _ in range(n - 1)])
#     # Додаємо початок (0) і кінець (total)
#     cuts = [0] + cuts + [total]
#     # Різниці між сусідніми точками будуть нашими випадковими числами
#     result = [cuts[i+1] - cuts[i] for i in range(len(cuts) - 1)]
#     return result

def generate_random_sum_with_individual_limits(n, total, limits):
    """Ця функція відповідає за те, щоб щоразу була інша кількість типів речень 
    серед неправильних відповідей, тому, спираючись на тип речення, а також на кількість доступних
    речень, функція повертає ліст з кількісним розподілом типів"""
    while True:
        # Генеруємо випадкові точки розподілу
        cuts = sorted([random.randint(0, total) for _ in range(n - 1)])
        # Додаємо початок (0) і кінець (total)
        cuts = [0] + cuts + [total]
        # Обчислюємо різниці між сусідніми точками
        result = [cuts[i+1] - cuts[i] for i in range(len(cuts) - 1)]
        # Перевіряємо, чи кожен елемент <= відповідного обмеження
        if all(result[i] <= limits[i] for i in range(len(result))):
            return result

def get_random_sentences_from_file(filename, num_sentences):
    """Витягуємо рандомні речення за назвою файлу і к-тю потрібних речень"""
    if num_sentences == 0:
        return []
    content = []
    print('Зашли і перевіряєм чи норм значення отримали', num_sentences)
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            content.append(line)
    if num_sentences >= len(content):
        return content  # Якщо запитано більше речень, ніж є у файлі, повертаємо всі
    else:
        sampled_sentences = random.sample(content, num_sentences)
        print("друкуємо наш результат", sampled_sentences)
        return sampled_sentences  # Вибираємо випадкові речення

def create_pdf(info):
    """Створюємо людям pdf"""
    if len(info) != 2:
        return info
    current_time = datetime.now()
    current_date = current_time.strftime("%d-%m")
    tasks, answers = info[0], info[1]
    pdf_file = f"bin_place_tests_here/{len(tasks)}tasks_sentence_type{current_date}{random.randint(0, 100)}.pdf"
    c = canvas.Canvas(pdf_file, pagesize=A4)

    # Встановлюємо початкові координати для тексту
    width, height = A4
    text_x = 50
    text_y = height - 50
    pdfmetrics.registerFont(TTFont('Arial', 'ArialMT.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'Arial-BoldMT.ttf'))

    for task in tasks:
    # Створюємо текстовий об'єкт і записуємо рядки
        text = c.beginText(text_x, text_y)
        text.setFont("Arial", 14)

        text.setLeading(16)

        for line in task:
            wrapped_lines = textwrap.wrap(line, width=73)
            for wrapped_line in wrapped_lines:
                if wrapped_line.startswith('Серед запропонованих варіантів'):
                    text.setFont("Arial-Bold", 14)
                else:
                    text.setFont("Arial", 14)
                text.textLine(wrapped_line)  # Додаємо рядок тексту
            text.textLine("")  # Порожній рядок для розділення між питаннями

        c.drawText(text)
        text_y -= 250
    c.showPage()  # Закінчуємо першу сторінку

    # Починаємо нову сторінку
    c.setFont("Arial", 14)  # Встановлюємо шрифт для нової сторінки

    # Створюємо текст для другої сторінки з відповідями
    answers_text = "\n".join([f"{ind+1}) {el}" for ind, el in enumerate(answers)])
    c.drawString(100, 750, f"Відповіді до ваших тестів:")  # Заголовок для відповідей
    c.drawString(100, 730, answers_text)  # Виводимо відповіді

    c.showPage()  # Завершуємо сторінку
    c.save()  # Зберігаємо PDF
    return pdf_file



if __name__ == "__main__":
    main('from_textes\\dovzhenko-oleksandr-petrovych-zacharovana-desna866 (1).docx', True)

    # exersize_mixed_sentances('Двоскладне')
    a = get_list_of_exersize(['Двоскладне', 'Складне безсполучникове'])
    create_pdf(a)
