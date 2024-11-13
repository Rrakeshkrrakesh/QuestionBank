import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
from io import BytesIO       # Import BytesIO


# Load the API key from Streamlit secrets
try:
    api_key = st.secrets["GEMINI_API_KEY"]  
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
except KeyError:
    st.error("API key not found in Streamlit secrets.")
    st.stop()
except Exception as e:
    st.error(f"An error occurred during API setup: {e}")
    st.stop()


def extract_text_from_pdf(file_contents):
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_contents))  # Wrap bytes in BytesIO
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None

def generate_questions(pdf_content):
    prompt = f"""You are an expert in the field related to the content of this PDF. Based on this PDF content, generate 5 multiple-choice questions, each with 4 options (A, B, C, D), and clearly indicate the correct answer. The questions should assess understanding of the key concepts and information presented in the PDF.

Format your response EXACTLY as follows:

Question 1:
A. Option 1
B. Option 2
C. Option 3
D. Option 4
Answer: A

Question 2:
A. Option 1
B. Option 2
C. Option 3
D. Option 4
Answer: B

... and so on for the remaining questions.

PDF content: {pdf_content}
"""
    response = model.content.generate(prompt=prompt)

    # Parse the response and extract questions and answers
    questions = []
    question_blocks = response.split('\n\n')
    for block in question_blocks:
        try:
            question_parts = block.split('\n')
            question_text = question_parts[0].strip()
            options = {'A': question_parts[1].split('B. ')[0].replace('A. ', '').strip(),
                       'B': question_parts[1].split('C. ')[0].replace('B. ', '').strip().split('B. ')[1],
                       'C': question_parts[1].split('D. ')[0].replace('C. ', '').strip().split('C. ')[1],
                       'D': question_parts[1].strip().split('D. ')[1]}

            answer_line = [line for line in question_parts if "Answer:" in line][0]
            answer = answer_line.split("Answer:")[1].strip()
            if answer in options:
                questions.append({"text": question_text, "options": options, "answer": answer})
        except Exception as e:
            print(f"Error parsing question: {block}. Error: {e}")

    return questions

def grade_difficulty(question):
    prompt = f"On a scale of 1 to 5 (1=very easy, 5=very hard), rate the difficulty of this question, considering the context of the provided document: \n{question}"
    response = model.content.generate(prompt=prompt)
    try:
        difficulty = int(response.strip())
        return difficulty
    except ValueError:
        return "Difficulty assessment unclear."

st.title("Interactive PDF Quiz")

uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

if uploaded_file:
    file_contents = uploaded_file.getvalue()
    pdf_text = extract_text_from_pdf(file_contents)

    if pdf_text:
        if "score" not in st.session_state:
            st.session_state.score = 0
        if "questions" not in st.session_state:
            st.session_state.questions = generate_questions(pdf_text)

        if st.session_state.questions:
            for i, question in enumerate(st.session_state.questions):
                st.write(f"**Question {i+1}:** {question['text']}")
                options = question["options"]
                user_answer = st.radio("Select your answer:", options.keys(), key=f"question_{i}")

                if user_answer == question["answer"]:
                    st.success("Correct!")
                    st.session_state.score += 1
                else:
                    st.error(f"Incorrect. The correct answer is {question['answer']}")

            st.write(f"Your current score: {st.session_state.score}")

        else:
            st.error("Error generating questions. Please check the PDF content or try again.")

    else:
        st.error("Could not extract text from PDF.")
