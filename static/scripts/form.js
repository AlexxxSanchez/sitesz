const form = document.getElementById('form');

function retrieveFormValue(event) {
    event.preventDefault();

    const nickname = form.querySelector('[name="nickname"]'),
    mail = form.querySelector('[name="mail"]'),
    text = form.querySelector('[name="text"]');

    const values = {
        nickname: nickname.value,
        mail: mail.value, 
        text: text.value
    };

    console.log('Nickname:', values.nickname);
    console.log('Email:', values.mail);
    console.log('Text:', values.text);
};

form.addEventListener('submit', retrieveFormValue);

