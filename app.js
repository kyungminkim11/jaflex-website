const embeddedImages={
  'jaflex-logo':'assets/embedded/jaflex-logo.b64',
  'hero-offshore':'assets/embedded/hero-offshore.b64',
  'coflexip-logo':'assets/embedded/coflexip-logo.b64',
  'coflex-hose':'assets/embedded/coflex-hose.b64',
  'world-bridge-logo':'assets/embedded/world-bridge-logo.b64',
  'wbi-interior-01':'assets/embedded/wbi-interior-01.b64',
  'wbi-interior-02':'assets/embedded/wbi-interior-02.b64',
  'wbi-floating-roof':'assets/embedded/wbi-floating-roof.b64',
  'wbi-roof-plant':'assets/embedded/wbi-roof-plant.b64',
  'wbi-dome-aerial-01':'assets/embedded/wbi-dome-aerial-01.b64',
  'wbi-dome-aerial-02':'assets/embedded/wbi-dome-aerial-02.b64',
  'wbi-dome-desert':'assets/embedded/wbi-dome-desert.b64'
};

Object.entries(embeddedImages).forEach(async([key,path])=>{
  try{
    const response=await fetch(path,{cache:'force-cache'});
    if(!response.ok) throw new Error(`${path}: ${response.status}`);
    const base64=(await response.text()).trim();
    document.querySelectorAll(`[data-legacy-key="${key}"]`).forEach(image=>{
      image.src=`data:image/webp;base64,${base64}`;
    });
  }catch(error){
    console.error('JAFLEX image load failed',key,error);
  }
});

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
