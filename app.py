from flask import Flask, render_template, request, send_file
from utils.doc_with_functions import main, get_list_of_exersize, create_pdf
import io

app = Flask(__name__)

# Список типів речень
sentence_types = ['Просте', 'Односкладне', 'Означено-особове', 'Неозначено-особове',
                  'Узагальнено-особове', 'Безособове', 'Двоскладне', 'Називне',
                  'Складносурядне', 'Складнопідрядне', 'Складне', 'Складне безсполучникове']

authors = {
    'Олександр Довженко': 'Зачарована Десна',
    'Леся Українка': 'Твої листи завше...',
    'Ольга Кобилянська': "Valse melancolique",
    'Валер\'ян Підмогильний': "Військовий літун",
    'Олекса Слісаренко': "Камінний виноград",
    'Василь Симоненко': "Чорна підкова",
    "Микола Хвильовий": "Елегія",
    "Юрій Яновський": "Дитинство"
}

author_file = {
    'Олександр Довженко': 'from_textes/dovzhenko-oleksandr-petrovych-zacharovana-desna866 (1).docx',
    'Леся Українка': "from_textes/ukrainka-lesia-tvoi-lysty-zavzhdy-pakhnut-zovialymy-troiandamy519.docx",
    'Ольга Кобилянська': "from_textes/kobylianska-olha-iulianivna-Valse-melancolique-(melankholiynyy-vals)2457.docx",
    'Валер\'ян Підмогильний': "from_textes/pidmohylnyy-valerian-petrovych-viyskovyy-litun1914.docx",
    'Олекса Слісаренко': "from_textes/slisarenko-oleksa-andriyovych-kaminnyy-vynohrad14227.docx",
    'Василь Симоненко': "from_textes/symonenko-vasyl-andriyovych-chorna-pidkova3660.docx",
    "Микола Хвильовий": "from_textes/khvylovyy-mykola-elehiia2717.docx",
    "Юрій Яновський": "from_textes/ianovskyy-iuriy-ivanovych-dytynstvo4896.docx"
}

@app.route('/')
def index():
    return render_template('index.html', sentence_types=sentence_types, authors=authors)

@app.route('/generate', methods=['POST'])
def generate():
    selected_author = request.form.get('author')  # selected_author = "Author1"
    num_tests = int(request.form.get('num_tests', 0))
    selected_types = [request.form.get(f'type_{i}') for i in range(num_tests)]
    defolt = author_file[selected_author]
    main(defolt)

    tests = get_list_of_exersize(selected_types)
    pdf_file_name = create_pdf(tests)

    # Читаємо створений PDF-файл і надсилаємо його користувачу
    with open(pdf_file_name, 'rb') as pdf_file:
        return send_file(io.BytesIO(pdf_file.read()), as_attachment=True, download_name=pdf_file_name, mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
