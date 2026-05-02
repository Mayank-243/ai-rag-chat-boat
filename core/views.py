from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import SignupForm
from django.contrib.auth.decorators import login_required

from .models import ChatHistory
import base64
from django.conf import settings
from groq import Groq
from langchain_core.prompts import ChatPromptTemplate

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login




def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("chatbot")
    else:
        form = SignupForm()

    return render(request, "signup.html", {"form": form})



def login_view(request):
    error = None

    if request.method == "POST":
        user_input = request.POST.get("username")   
        password = request.POST.get("password")

        
        user = User.objects.filter(email=user_input).first()

        if user:
            username = user.username   
        else:
            username = user_input     

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("chatbot")
        else:
            error = "Invalid username/email or password"

    return render(request, "login.html", {"error": error})



@login_required
def logout(request):
    return redirect("signup")

def get_ai_answer(question, history, image=None):
    client = Groq(api_key=settings.GROQ_API_KEY)

    system_prompt = """
You are an advanced AI chatbot and teacher.

Rules:
- Talk like a real human.
- Answer in simple Hinglish.
- Use previous chat history for context.
- If an image is given, first describe the image clearly.
- Then answer the user's question.
- Give helpful and clear answers.
"""

    user_content = [
        {
            "type": "text",
            "text": f"""
Previous Chat:
{history}

User Question:
{question}
"""
        }
    ]

    if image:
        image_base64 = encode_image(image)

        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{image.content_type};base64,{image_base64}"
            }
        })

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        temperature=0.7,
        max_tokens=700,
    )

    return response.choices[0].message.content
@login_required
def chatbot(request):

    if request.method == "POST":
        question = request.POST.get("question")
        image = request.FILES.get("image")  

        previous_chats = ChatHistory.objects.filter(
            user=request.user
        ).order_by("-created_at")[:5]

        history_text = ""
        for chat in reversed(previous_chats):
            history_text += f"User: {chat.question}\nAI: {chat.answer}\n"

        answer = get_ai_answer(question, history_text, image)

        ChatHistory.objects.create(
            user=request.user,
            question=question,
            answer=answer,
            image=image,         
            status="pending"
        )

    chats = ChatHistory.objects.filter(user=request.user).order_by("-created_at")

    return render(request, "chatbot.html", {"chats": chats})

def encode_image(image_file):
    image_file.seek(0)   
    return base64.b64encode(image_file.read()).decode("utf-8")