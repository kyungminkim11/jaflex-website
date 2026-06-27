const menu=document.querySelector('.menu');
const nav=document.querySelector('.nav');
menu?.addEventListener('click',()=>{
  const open=menu.getAttribute('aria-expanded')==='true';
  menu.setAttribute('aria-expanded',String(!open));
  nav?.classList.toggle('open',!open);
});
nav?.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{
  nav.classList.remove('open');
  menu?.setAttribute('aria-expanded','false');
}));
const form=document.querySelector('#contact-form');
form?.addEventListener('submit',event=>{
  event.preventDefault();
  const status=form.querySelector('.form-status');
  if(status) status.textContent='現在、送信機能を準備しています。お問い合わせ内容はまだ送信されていません。';
});
