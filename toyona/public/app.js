(() => {
  const tg = window.Telegram?.WebApp;
  tg?.ready();
  tg?.expand();
  tg?.setHeaderColor?.('#f5f7f5');
  tg?.setBackgroundColor?.('#f5f7f5');

  const state = { user:null, currentPrice:150000, friends:[], weddings:[], gifts:[], page:'home', query:'', selectedWedding:null, selectedFriend:null, busy:false };
  const app = document.getElementById('app');
  const modal = document.getElementById('modal');
  const modalBody = document.getElementById('modalBody');
  const modalTitle = document.getElementById('modalTitle');
  const modalSave = document.getElementById('modalSave');
  let modalHandler = null;
  let toastTimer = null;

  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = n => Math.round(Number(n)||0).toLocaleString('uz-UZ').replace(/,/g,' ') + ' so‘m';
  const compactMoney = n => {
    n = Number(n)||0;
    if (Math.abs(n) >= 1e9) return (n/1e9).toFixed(1).replace('.',',')+' mlrd';
    if (Math.abs(n) >= 1e6) return (n/1e6).toFixed(1).replace('.',',')+' mln';
    return Math.round(n).toLocaleString('uz-UZ').replace(/,/g,' ');
  };
  const kg = n => (Math.round((Number(n)||0)*10)/10).toLocaleString('uz-UZ');
  const dateText = d => d ? new Date(String(d).slice(0,10)+'T12:00:00').toLocaleDateString('uz-UZ',{day:'numeric',month:'short',year:'numeric'}) : 'Sana kiritilmagan';
  const friend = id => state.friends.find(x=>x.id===id);
  const wedding = id => state.weddings.find(x=>x.id===id);
  const gift = (wid,fid) => state.gifts.find(x=>x.wedding_id===wid && x.friend_id===fid);
  const weddingGifts = wid => state.gifts.filter(g=>g.wedding_id===wid);
  const amount = (wid,fid) => Number(gift(wid,fid)?.amount||0);
  const meatPrice = w => Number(w?.meat_price||state.currentPrice);
  const meatKg = g => Number(g.amount||0) / Number(g.meat_price||state.currentPrice);
  const allGiftSum = () => state.gifts.reduce((s,g)=>s+Number(g.amount||0),0);
  const allGiftKg = () => state.gifts.reduce((s,g)=>s+meatKg(g),0);
  const escapeCsvName = s => String(s||'').replace(/[^\w.-]+/g,'_');

  async function api(url, options={}) {
    const headers = {'Content-Type':'application/json', ...(options.headers||{})};
    if (tg?.initData) headers['X-Telegram-Init-Data'] = tg.initData;
    const response = await fetch(url,{...options,headers});
    const type = response.headers.get('content-type')||'';
    if (!response.ok) {
      let message = 'Xatolik yuz berdi.';
      try { message = (await response.json()).error || message; } catch {}
      throw new Error(message);
    }
    return type.includes('application/json') ? response.json() : response;
  }
  async function load(showLoading=true) {
    if (showLoading) app.innerHTML='<div class="loading"><span class="spinner"></span> Ma’lumotlar yuklanmoqda...</div>';
    try {
      const data = await api('/api/bootstrap');
      Object.assign(state,data);
      const first = state.user?.first_name ? `${state.user.first_name}, xush kelibsiz!` : 'Hisob-kitoblaringiz bir joyda';
      document.getElementById('greeting').textContent=first;
      render();
    } catch (e) {
      app.innerHTML=`<div class="empty"><div class="empty-icon">☁️</div><b>Ulanib bo‘lmadi</b><p>${esc(e.message)}</p><button class="btn primary" id="retryBtn">Qayta urinish</button><p class="note">Mini App’ni Telegram bot menyusidan oching. Server va ma’lumotlar ombori ishlayotganini tekshiring.</p></div>`;
    }
  }
  function toast(message) {
    const el=document.getElementById('toast'); el.textContent=message;el.classList.add('show');
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),2800);
    tg?.HapticFeedback?.notificationOccurred?.('success');
  }
  function fail(e) { toast(e.message||'Xatolik yuz berdi.'); tg?.HapticFeedback?.notificationOccurred?.('error'); }
  function setPage(page) {
    state.page=page; state.query=''; state.selectedWedding=null; state.selectedFriend=null;
    document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
    render(); window.scrollTo({top:0,behavior:'smooth'});
  }
  function empty(icon,title,sub,button='') {
    return `<div class="empty"><div class="empty-icon">${icon}</div><b>${title}</b><div>${sub}</div>${button?`<div style="margin-top:13px">${button}</div>`:''}</div>`;
  }
  function button(text,action,cls='primary',extra='') { return `<button class="btn ${cls}" data-action="${action}" ${extra}>${text}</button>`; }
  function section(title,sub='',action='') { return `<div class="section-head"><h2>${title}</h2><div class="card-row"><span class="subtle">${sub}</span>${action}</div></div>`; }
  function stats(items) { return `<div class="stats">${items.map(x=>`<div class="stat"><b>${x.value}</b><span>${x.label}</span></div>`).join('')}</div>`; }
  function weddingTotal(w) { return weddingGifts(w.id).reduce((s,g)=>s+Number(g.amount),0); }
  function weddingCard(w) {
    const gs=weddingGifts(w.id), total=weddingTotal(w), count=gs.length, kgTotal=gs.reduce((s,g)=>s+meatKg(g),0);
    return `<button class="card list-card" data-action="open-wedding" data-id="${w.id}"><div class="card-row"><div><div class="card-title">${esc(w.name)} to‘yi</div><div class="muted">${dateText(w.wedding_date)} · ${money(meatPrice(w))}/kg</div></div><span class="tag">${count}/${state.friends.length}</span></div><div class="card-row" style="margin-top:12px"><div><div class="amount">${compactMoney(total)} <span class="muted">so‘m</span></div><div class="muted">${kg(kgTotal)} kg ekvivalent</div></div><span class="green">Batafsil ›</span></div><div class="progress"><span style="width:${state.friends.length?Math.min(100,count/state.friends.length*100):0}%"></span></div></button>`;
  }
  function friendStats(f) {
    const gifts=state.gifts.filter(g=>g.friend_id===f.id);
    return {gifts, total:gifts.reduce((s,g)=>s+Number(g.amount),0), kg:gifts.reduce((s,g)=>s+meatKg(g),0)};
  }
  function friendCard(f) {
    const s=friendStats(f);
    return `<button class="card list-card" data-action="open-friend" data-id="${f.id}"><div class="card-row"><div><div class="card-title">${esc(f.name)}</div><div class="muted">${s.gifts.length} ta to‘yda qatnashgan</div></div><div class="right"><div class="amount">${kg(s.kg)} kg</div><div class="muted">jami ekvivalent</div></div></div></button>`;
  }
  function homePage() {
    const recent=[...state.weddings].slice(0,3);
    return `<section class="hero"><div class="eyebrow">BARCHA TO‘YONALAR</div><div class="hero-total">${money(allGiftSum())}</div><div class="hero-sub">Kiritilgan to‘yonalarning umumiy summasi</div><div class="hero-grid"><div class="hero-mini"><b>${state.weddings.length}</b><span>Jami to‘ylar</span></div><div class="hero-mini"><b>${state.friends.length}</b><span>Oshnalar</span></div></div></section>
      ${stats([{value:kg(allGiftKg())+' kg',label:'Jami go‘sht ekvivalenti'},{value:state.gifts.length,label:'To‘yona yozuvlari'},{value:money(state.currentPrice),label:'Bugungi 1 kg narxi'}])}
      ${section('So‘nggi to‘ylar','',button('+ To‘y qo‘shish','add-wedding','primary small'))}
      ${recent.length?`<div class="list">${recent.map(weddingCard).join('')}</div>`:empty('🤝','Hali to‘y qo‘shilmagan','Birinchi to‘yni qo‘shib, to‘yona hisobini yuritishni boshlang.',button('Birinchi to‘y +','add-wedding'))}
      ${section('Tezkor amallar')}
      <div class="form-grid"><button class="card list-card" data-action="add-friend"><div class="card-title">＋ Oshna qo‘shish</div><div class="muted">Ro‘yxatni kengaytirish</div></button><button class="card list-card" data-action="go-reports"><div class="card-title">▤ Hisobot</div><div class="muted">Umumiy natijalarni ko‘rish</div></button></div>`;
  }
  function weddingsPage() {
    const q=state.query.toLocaleLowerCase('uz');
    const list=state.weddings.filter(w=>(w.name||'').toLocaleLowerCase('uz').includes(q)||(w.wedding_date||'').includes(q));
    return `<h2 class="page-title">To‘ylar</h2><p class="page-sub">To‘ylarni, sanalarni va to‘yona yig‘imini boshqaring.</p>
      <div class="search-wrap"><span class="search-icon">⌕</span><input id="searchInput" placeholder="To‘y nomi yoki sana..." value="${esc(state.query)}"></div>
      <div class="action-row" style="margin-bottom:14px">${button('+ To‘y qo‘shish','add-wedding')}</div>
      ${list.length?`<div class="list">${list.map(weddingCard).join('')}</div>`:empty('🗓️',state.query?'Natija topilmadi':'Hali to‘y yo‘q',state.query?'Boshqa so‘z bilan qidirib ko‘ring.':'Yangi to‘y qo‘shish tugmasini bosing.')}`;
  }
  function friendsPage() {
    const q=state.query.toLocaleLowerCase('uz');
    const list=state.friends.filter(f=>f.name.toLocaleLowerCase('uz').includes(q));
    return `<h2 class="page-title">Oshnalar</h2><p class="page-sub">Do‘stlar ro‘yxati va har birining to‘yona tarixi.</p>
      <div class="search-wrap"><span class="search-icon">⌕</span><input id="searchInput" placeholder="Oshna ismini qidiring..." value="${esc(state.query)}"></div>
      <div class="action-row" style="margin-bottom:14px">${button('+ Oshna qo‘shish','add-friend')}</div>
      ${list.length?`<div class="list">${list.map(friendCard).join('')}</div>`:empty('♙',state.query?'Natija topilmadi':'Oshnalar ro‘yxati bo‘sh','Ism qo‘shib, to‘yonalarni qayd eting.')}`;
  }
  function weddingDetail(id) {
    const w=wedding(id);if(!w){state.selectedWedding=null;return weddingsPage();}
    const gs=weddingGifts(id),total=weddingTotal(w), minAmount=Math.round(Number(w.min_kg)*meatPrice(w));
    const list=state.friends.map(f=>{
      const g=gift(id,f.id),a=Number(g?.amount||0);
      // Reciprocal to‘yona: how much this wedding's owner previously gave at this friend's wedding(s).
      const ownerId=w.friend_id;
      const historicalKg=ownerId?state.gifts.filter(x=>x.friend_id===ownerId && wedding(x.wedding_id)?.friend_id===f.id).reduce((s,x)=>s+meatKg(x),0):0;
      const due=Math.max(0,historicalKg*state.currentPrice-a);
      return `<div class="card"><div class="gift-row"><div><div class="gift-name">${a?'✓ ':''}${esc(f.name)}</div><div class="gift-kg">${a?`${kg(meatKg(g))} kg · ${money(a)}`:'Hali kiritilmagan'}</div>${a>0&&a<minAmount?'<div class="muted" style="color:var(--orange);margin-top:4px">Minimumdan kam</div>':''}${due>0?`<div class="debt-line">Oldingi to‘yonalar bo‘yicha taxminiy tavsiya: ${money(due)} <button class="btn secondary small" data-action="fill-due" data-friend="${f.id}" data-wedding="${id}" data-amount="${Math.round(due)}">Summani yozish</button></div>`:''}</div><input class="gift-input" inputmode="numeric" type="number" min="0" step="1000" placeholder="So‘m" aria-label="${esc(f.name)} to‘yonasi" data-gift-input data-wedding="${id}" data-friend="${f.id}" value="${a||''}"></div></div>`;
    }).join('');
    return `<button class="btn secondary small" data-action="back-weddings">‹ To‘ylar</button><div class="section-head"><h2>${esc(w.name)} to‘yi</h2></div><p class="page-sub">${dateText(w.wedding_date)} · ${money(meatPrice(w))}/kg · minimum ${kg(w.min_kg)} kg (${money(minAmount)})</p>
      ${stats([{value:compactMoney(total),label:'Jami so‘m'},{value:kg(gs.reduce((s,g)=>s+meatKg(g),0))+' kg',label:'Go‘sht ekvivalenti'},{value:`${gs.length}/${state.friends.length}`,label:'To‘yona bergan'}])}
      <div class="action-row">${button('✎ To‘yni tahrirlash','edit-wedding','secondary')}${button('O‘chirish','delete-wedding','danger')}</div>
      <div class="section-head"><h2>To‘yona ro‘yxati</h2><span class="subtle">Summa kiriting</span></div>
      ${state.friends.length?list:empty('♙','Oshnalar yo‘q','Avval Oshnalar bo‘limidan ism qo‘shing.')}
      <p class="note">Summa maydonidan chiqishingiz bilan saqlanadi. Kg ekvivalenti shu to‘y uchun belgilangan narx bo‘yicha hisoblanadi.</p>`;
  }
  function friendDetail(id) {
    const f=friend(id);if(!f){state.selectedFriend=null;return friendsPage();}
    const gs=state.gifts.filter(g=>g.friend_id===id).sort((a,b)=>String(wedding(b.wedding_id)?.wedding_date||'').localeCompare(String(wedding(a.wedding_id)?.wedding_date||'')));
    const kgTotal=gs.reduce((s,g)=>s+meatKg(g),0), total=gs.reduce((s,g)=>s+Number(g.amount),0);
    const due=kgTotal*state.currentPrice;
    return `<button class="btn secondary small" data-action="back-friends">‹ Oshnalar</button><div class="section-head"><h2>${esc(f.name)}</h2></div>
      ${stats([{value:money(total),label:'Jami bergan'},{value:kg(kgTotal)+' kg',label:'Go‘sht ekvivalenti'},{value:money(due),label:'Bugungi narxda'}])}
      <div class="action-row">${button('✎ Ismni tahrirlash','edit-friend','secondary')}${button('O‘chirish','delete-friend','danger')}</div>
      <div class="card"><div class="field"><label>Bugungi 1 kg go‘sht narxi (so‘m)</label><input type="number" min="1" step="1000" id="currentPriceInput" value="${state.currentPrice}"></div><p class="note">Bu narx faqat taxminiy qaytarish qiymatini ko‘rsatadi. Eski yozuvlar o‘z tarixiy narxida qoladi.</p><div class="card-row"><b>Taxminiy qaytarish qiymati</b><b class="amount">${money(due)}</b></div></div>
      ${section('To‘yona tarixi',`${gs.length} ta yozuv`)}
      ${gs.length?`<div class="list">${gs.map(g=>{const w=wedding(g.wedding_id);return w?`<div class="card"><div class="card-row"><div><div class="card-title">${esc(w.name)} to‘yi</div><div class="muted">${dateText(w.wedding_date)}</div></div><div class="right"><div class="amount">${money(g.amount)}</div><div class="muted">${kg(meatKg(g))} kg</div></div></div><button class="btn secondary small" style="margin-top:10px" data-action="open-wedding" data-id="${w.id}">Yozuvni ko‘rish</button></div>`:''}).join('')}</div>`:empty('🧾','Hali to‘yona yozilmagan','Bu oshna uchun to‘yona kiritilmagan.')}`;
  }
  function reportsPage() {
    const totalsByWedding=state.weddings.map(w=>({w,total:weddingTotal(w),count:weddingGifts(w.id).length})).sort((a,b)=>b.total-a.total);
    return `<h2 class="page-title">Hisobot</h2><p class="page-sub">Umumiy ko‘rsatkichlar va Excel’da ochiladigan CSV fayl.</p>
      ${stats([{value:money(allGiftSum()),label:'Jami to‘yona'},{value:kg(allGiftKg())+' kg',label:'Jami kg ekv.'},{value:state.gifts.length,label:'Yozuvlar'}])}
      <div class="card"><div class="card-title">Bugungi go‘sht narxi</div><p class="muted">Taxminiy qaytarish qiymatlarini hisoblash uchun ishlatiladi.</p><div class="field" style="margin-top:12px"><input id="reportPrice" type="number" min="1" step="1000" value="${state.currentPrice}"></div>${button('Narxni saqlash','save-price','primary full')}</div>
      ${section('To‘ylar bo‘yicha jamlanma')}
      ${totalsByWedding.length?`<div class="list">${totalsByWedding.map(x=>`<div class="card"><div class="card-row"><div><div class="card-title">${esc(x.w.name)} to‘yi</div><div class="muted">${dateText(x.w.wedding_date)} · ${x.count} kishi</div></div><div class="right"><div class="amount">${compactMoney(x.total)}</div><div class="muted">so‘m</div></div></div></div>`).join('')}</div>`:empty('▤','Hisobot hali bo‘sh','To‘y va to‘yona qo‘shilgach, jamlanma shu yerda ko‘rinadi.')}
      <div class="card"><div class="card-title">Hisobotni yuklab olish</div><p class="muted">Har bir to‘y, oshna, summa, tarixiy narx va izohlar CSV faylga chiqariladi. Excel’da ochishingiz mumkin.</p>${button('↓ CSV hisobotni yuklab olish','export-csv','primary full')}</div>
      <p class="note">Hisobot faqat sizning Telegram profilingizga tegishli ma’lumotlarni o‘z ichiga oladi.</p>`;
  }
  function render() {
    document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===state.page));
    if(state.selectedWedding) app.innerHTML=weddingDetail(state.selectedWedding);
    else if(state.selectedFriend) app.innerHTML=friendDetail(state.selectedFriend);
    else if(state.page==='home') app.innerHTML=homePage();
    else if(state.page==='weddings') app.innerHTML=weddingsPage();
    else if(state.page==='friends') app.innerHTML=friendsPage();
    else app.innerHTML=reportsPage();
  }
  function openModal(title,body,handler,saveText='Saqlash') {
    modalTitle.textContent=title;modalBody.innerHTML=body;modalHandler=handler;modalSave.textContent=saveText;
    modalSave.disabled=false;
    if(!modal.open) modal.showModal();
  }
  function field(label,name,value='',type='text',extra='') {
    return `<div class="field"><label for="${name}">${label}</label><input id="${name}" name="${name}" type="${type}" value="${esc(value)}" ${extra}></div>`;
  }
  function addFriend() {
    openModal('Yangi oshna',field('Oshna ismi','friendName','','text','maxlength="100" required placeholder="Masalan, Azizbek"'),async()=>{
      const name=document.getElementById('friendName').value.trim();if(!name)throw new Error('Ism kiriting.');
      await api('/api/friends',{method:'POST',body:JSON.stringify({name})});await load(false);toast('Oshna qo‘shildi.');
    });
  }
  function editFriend() {
    const f=friend(state.selectedFriend);if(!f)return;
    openModal('Oshna ma’lumotini tahrirlash',field('Ism','friendName',f.name,'text','maxlength="100" required'),async()=>{
      const name=document.getElementById('friendName').value.trim();if(!name)throw new Error('Ism kiriting.');
      await api('/api/friends/'+f.id,{method:'PUT',body:JSON.stringify({name})});await load(false);toast('Ma’lumot yangilandi.');
    });
  }
  function addWedding() {
    const options=state.friends.map(f=>`<option value="${f.id}">${esc(f.name)}</option>`).join('');
    openModal('Yangi to‘y',`${state.friends.length?`<div class="field"><label>To‘y egasi (oshna)</label><select id="wFriend"><option value="">Tanlanmagan</option>${options}</select></div>`:`<p class="note">Hozircha oshnalar ro‘yxati bo‘sh. To‘y nomini kiritishingiz mumkin, keyin oshna qo‘shing.</p>`}
      ${field('To‘y nomi','wName','','text','required maxlength="100" placeholder="Masalan, Azizbekning to‘yi"')}
      <div class="form-grid">${field('Sana','wDate','','date')}${field('Go‘sht narxi (so‘m/kg)','wPrice',state.currentPrice,'number','min="1" required')}</div>
      <div class="form-grid">${field('Minimum (kg)','wMin','2','number','min="0" max="100" step="0.5" required')}${field('Izoh','wNote','','text','maxlength="500" placeholder="Ixtiyoriy"')}</div>`,async()=>{
      const name=document.getElementById('wName').value.trim(), meatPriceValue=Number(document.getElementById('wPrice').value), minKg=Number(document.getElementById('wMin').value);
      if(!name)throw new Error('To‘y nomini kiriting.');if(!Number.isSafeInteger(meatPriceValue)||meatPriceValue<1)throw new Error('Go‘sht narxini to‘g‘ri kiriting.');
      await api('/api/weddings',{method:'POST',body:JSON.stringify({friendId:document.getElementById('wFriend')?.value||'',name,date:document.getElementById('wDate').value,meatPrice:meatPriceValue,minKg,note:document.getElementById('wNote').value})});
      await api('/api/settings',{method:'PUT',body:JSON.stringify({currentPrice:meatPriceValue})});await load(false);toast('To‘y qo‘shildi.');
    });
  }
  function editWedding() {
    const w=wedding(state.selectedWedding);if(!w)return;
    const options=state.friends.map(f=>`<option value="${f.id}" ${f.id===w.friend_id?'selected':''}>${esc(f.name)}</option>`).join('');
    openModal('To‘yni tahrirlash',`<div class="field"><label>To‘y egasi</label><select id="wFriend"><option value="">Tanlanmagan</option>${options}</select></div>
      ${field('To‘y nomi','wName',w.name,'text','required maxlength="100"')}
      <div class="form-grid">${field('Sana','wDate',w.wedding_date?String(w.wedding_date).slice(0,10):'','date')}${field('Go‘sht narxi (so‘m/kg)','wPrice',w.meat_price,'number','min="1" required')}</div>
      <div class="form-grid">${field('Minimum (kg)','wMin',w.min_kg,'number','min="0" max="100" step="0.5" required')}${field('Izoh','wNote',w.note||'','text','maxlength="500"')}</div>
      <p class="note">To‘y narxini o‘zgartirish avval kiritilgan to‘yona yozuvlarining tarixiy kg narxini o‘zgartirmaydi.</p>`,async()=>{
      const name=document.getElementById('wName').value.trim(),price=Number(document.getElementById('wPrice').value),minKg=Number(document.getElementById('wMin').value);
      if(!name||!Number.isSafeInteger(price)||price<1||!Number.isFinite(minKg)||minKg<0)throw new Error('Maydonlarni tekshiring.');
      await api('/api/weddings/'+w.id,{method:'PUT',body:JSON.stringify({friendId:document.getElementById('wFriend').value,name,date:document.getElementById('wDate').value,meatPrice:price,minKg,note:document.getElementById('wNote').value})});
      await load(false);toast('To‘y yangilandi.');
    });
  }
  async function confirmDelete(title,body,endpoint,onDone) {
    openModal(title,`<p>${body}</p><p class="note">Bu amalni ortga qaytarib bo‘lmaydi.</p>`,async()=>{await api(endpoint,{method:'DELETE'});state.selectedWedding=null;state.selectedFriend=null;await load(false);onDone?.();toast('Ma’lumot o‘chirildi.');},'Ha, o‘chirish');
    modalSave.classList.add('danger');
  }
  async function saveGift(input) {
    const wid=input.dataset.wedding,fid=input.dataset.friend;
    const raw=String(input.value||'').trim(), amountValue=raw===''?0:Number(raw);
    if(!Number.isSafeInteger(amountValue)||amountValue<0){toast('Summani musbat butun son kiriting.');return;}
    input.disabled=true;
    try {
      await api('/api/gifts',{method:'PUT',body:JSON.stringify({weddingId:wid,friendId:fid,amount:amountValue})});
      await load(false);toast(amountValue?'To‘yona saqlandi.':'To‘yona yozuvi o‘chirildi.');
    } catch(e){fail(e);input.disabled=false;}
  }
  async function fillDue(el) {
    const input=document.querySelector(`[data-gift-input][data-wedding="${el.dataset.wedding}"][data-friend="${el.dataset.friend}"]`);
    if(input){input.value=el.dataset.amount;await saveGift(input);}
  }
  async function exportCsv() {
    const response=await api('/api/export.csv');
    const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download='toyona-hisoboti.csv';document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);toast('Hisobot tayyor.');
  }

  document.addEventListener('click',async e=>{
    const nav=e.target.closest('[data-page]');
    if(nav){setPage(nav.dataset.page);return;}
    const el=e.target.closest('[data-action]');
    if(!el)return;
    const a=el.dataset.action;
    try {
      if(a==='add-friend')addFriend();
      else if(a==='add-wedding')addWedding();
      else if(a==='open-wedding'){state.selectedWedding=el.dataset.id;state.selectedFriend=null;render();window.scrollTo(0,0);}
      else if(a==='open-friend'){state.selectedFriend=el.dataset.id;state.selectedWedding=null;render();window.scrollTo(0,0);}
      else if(a==='back-weddings'){state.selectedWedding=null;setPage('weddings');}
      else if(a==='back-friends'){state.selectedFriend=null;setPage('friends');}
      else if(a==='edit-friend')editFriend();
      else if(a==='edit-wedding')editWedding();
      else if(a==='delete-wedding'){const w=wedding(state.selectedWedding);if(w)confirmDelete('To‘yni o‘chirish',`“${w.name}” to‘yi va unga tegishli barcha to‘yona yozuvlari o‘chiriladi.`, '/api/weddings/'+w.id);}
      else if(a==='delete-friend'){const f=friend(state.selectedFriend);if(f)confirmDelete('Oshnani o‘chirish',`“${f.name}” va unga tegishli to‘yona yozuvlari o‘chiriladi.`, '/api/friends/'+f.id);}
      else if(a==='fill-due')await fillDue(el);
      else if(a==='save-price'){
        const p=Number(document.getElementById('reportPrice').value);if(!Number.isSafeInteger(p)||p<1)throw new Error('Narxni to‘g‘ri kiriting.');
        await api('/api/settings',{method:'PUT',body:JSON.stringify({currentPrice:p})});await load(false);toast('Narx saqlandi.');
      }
      else if(a==='export-csv')await exportCsv();
      else if(a==='go-reports')setPage('reports');
    } catch(err){fail(err);}
  });
  document.addEventListener('submit',e=>e.preventDefault());
  modal.addEventListener('click',e=>{if(e.target===modal)modal.close();});
  modal.addEventListener('close',()=>{modalHandler=null;modalSave.classList.remove('danger');});
  modalSave.addEventListener('click',async e=>{
    if(!modalHandler)return;
    e.preventDefault();modalSave.disabled=true;modalSave.textContent='Saqlanmoqda...';
    try{await modalHandler();modal.close();}
    catch(err){fail(err);}
    finally{modalSave.disabled=false;modalSave.textContent='Saqlash';}
  });
  document.addEventListener('change',async e=>{
    if(e.target.matches('[data-gift-input]'))await saveGift(e.target);
    if(e.target.id==='currentPriceInput'||e.target.id==='reportPrice'){
      const p=Number(e.target.value);
      if(Number.isSafeInteger(p)&&p>0){try{await api('/api/settings',{method:'PUT',body:JSON.stringify({currentPrice:p})});state.currentPrice=p;await load(false);toast('Narx yangilandi.');}catch(err){fail(err);}}
    }
  });
  document.addEventListener('input',e=>{
    if(e.target.id==='searchInput'){
      const pos=e.target.selectionStart;state.query=e.target.value;render();
      const input=document.getElementById('searchInput');input?.focus();input?.setSelectionRange(pos,pos);
    }
  });
  document.getElementById('refreshBtn').addEventListener('click',()=>load(true));
  document.addEventListener('click',e=>{if(e.target.id==='retryBtn')load(true);});
  if(tg?.onEvent)tg.onEvent('themeChanged',()=>{});
  load(true);
})();
