#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 3 — Gera app.html: dashboard com login Supabase Auth.
Cada usuário autentica no servidor e o RLS entrega apenas o payload
do seu escopo (admin / superintendente / regional).

Rodar de novo sempre que o dashboard_template_metas.html mudar.
"""
import sys, re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SISTEMA_DIR = Path(__file__).parent
BASE_DIR    = SISTEMA_DIR.parent
TEMPLATE    = SISTEMA_DIR / "dashboard_template_metas.html"
SAIDA       = BASE_DIR / "app.html"

import base64
_logo_png = (Path(__file__).parent.parent / "assets" / "logo branca.png")
LOGO_B64 = ("data:image/png;base64," + base64.b64encode(_logo_png.read_bytes()).decode()) if _logo_png.exists() else ""

SUPA_URL = "https://drokcguxofvmdrnmedrx.supabase.co"
SUPA_KEY = "sb_publishable_AhOot6J1thyzjMKzuMqUvw_JfbbNf6m"  # chave pública

LOADER = """const SUPA_URL='__SUPA_URL__';
const SUPA_KEY='__SUPA_KEY__';
let DATA=null, DIG_DATA=[], DIG_ESTRATEGICOS=new Set(), DIG_PERIODO='';
const AUTH_DATA=[];
let _AUTH=null, _URL_REGIONAL='', _URL_SUPER=null, _URL_COMERCIAL=null;
const _IS_LOCAL=false;

function _sbHeaders(tok){return {apikey:SUPA_KEY, Authorization:'Bearer '+(tok||SUPA_KEY), 'Content-Type':'application/json'};}

function _showLogin(msg){
  return new Promise(res=>{
    let ov=document.getElementById('sb-login-ov');
    if(!ov){
      ov=document.createElement('div'); ov.id='sb-login-ov';
      const _sbTheme=localStorage.getItem('sb_theme')||'dark';
      const _sbSize=localStorage.getItem('sb_font_size')||'100';
      ov.setAttribute('data-theme',_sbTheme);
      ov.style.setProperty('--nv-font-scale', _sbSize==='100'?'1':_sbSize==='125'?'1.25':'1.55');
      ov.innerHTML='<div class="sb-card">'
        +'<div class="sb-a11y-bar"><button class="sb-theme-btn" id="sb-theme-btn" aria-label="Alternar tema">&#9790; Tema</button>'
        +'<div class="sb-font-btns">'
        +'<button class="sb-fs-btn'+(_sbSize==='100'?' active':'')+'" data-size="100" aria-label="Texto normal">A</button>'
        +'<button class="sb-fs-btn'+(_sbSize==='125'?' active':'')+'" data-size="125" aria-label="Texto maior">A+</button>'
        +'<button class="sb-fs-btn'+(_sbSize==='155'?' active':'')+'" data-size="155" aria-label="Texto m\u00e1ximo">A++</button>'
        +'</div></div>'
        +'<div class="sb-logo-wrap"><img src="__LOGO_B64__" alt="NOVA PROMOTORA" style="width:190px;max-width:80%"></div>'
        +'<p class="sb-subtitle">Gest\u00e3o Comercial</p>'
        +'<div id="sb-err" class="sb-err" style="display:none" role="alert"></div>'
        +'<label class="sb-label" for="sb-email">E-mail</label>'
        +'<input id="sb-email" class="sb-input" type="email" placeholder="seu.email@novapromotora.com" autocomplete="username">'
        +'<label class="sb-label" for="sb-senha">Senha</label>'
        +'<div class="sb-pw-wrap"><input id="sb-senha" class="sb-input sb-input-pw" type="password" placeholder="Senha" autocomplete="current-password">'
        +'<button class="sb-eye" id="sb-eye" type="button" aria-label="Mostrar/ocultar senha"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></button></div>'
        +'<button id="sb-entrar" class="sb-btn-primary">Entrar</button>'
        +'</div>';
      document.body.appendChild(ov);
    }
    const err=document.getElementById('sb-err');
    if(msg){err.textContent=msg;err.style.display='block';}
    const tenta=async()=>{
      const email=document.getElementById('sb-email').value.trim().toLowerCase();
      const senha=document.getElementById('sb-senha').value;
      const btn=document.getElementById('sb-entrar');
      btn.textContent='Verificando...';btn.disabled=true;
      try{
        const r=await fetch(SUPA_URL+'/auth/v1/token?grant_type=password',{method:'POST',headers:_sbHeaders(),body:JSON.stringify({email,password:senha})});
        const j=await r.json();
        if(!r.ok||!j.access_token){
          err.textContent='Usu\\u00e1rio ou senha incorretos';err.style.display='block';
          btn.textContent='Entrar';btn.disabled=false;return;
        }
        localStorage.setItem('sb_sess',JSON.stringify({t:j.access_token,e:email,exp:Date.now()+(j.expires_in||3600)*1000}));
        ov.remove();res();
      }catch(ex){
        err.textContent='Erro de conex\\u00e3o: '+ex.message;err.style.display='block';
        btn.textContent='Entrar';btn.disabled=false;
      }
    };
    document.getElementById('sb-entrar').onclick=tenta;
    ['sb-email','sb-senha'].forEach(id=>document.getElementById(id).addEventListener('keydown',ev=>{if(ev.key==='Enter')tenta();}));
    document.getElementById('sb-theme-btn').addEventListener('click',function(){
      const o=document.getElementById('sb-login-ov');
      const t=o.getAttribute('data-theme')==='dark'?'light':'dark';
      o.setAttribute('data-theme',t);localStorage.setItem('sb_theme',t);
    });
    document.querySelectorAll('#sb-login-ov .sb-fs-btn').forEach(b=>b.addEventListener('click',function(){
      const o=document.getElementById('sb-login-ov');
      const sz=this.dataset.size;
      o.style.setProperty('--nv-font-scale',sz==='100'?'1':sz==='125'?'1.25':'1.55');
      localStorage.setItem('sb_font_size',sz);
      document.querySelectorAll('#sb-login-ov .sb-fs-btn').forEach(x=>x.classList.remove('active'));
      this.classList.add('active');
    }));
    document.getElementById('sb-eye').addEventListener('click',function(){
      const pw=document.getElementById('sb-senha');
      pw.type=pw.type==='password'?'text':'password';
    });
  });
}

function _sbTrocarSenha(){
  let ov=document.createElement('div');
  ov.style.cssText='position:fixed;inset:0;background:rgba(5,5,15,.75);display:flex;align-items:center;justify-content:center;z-index:9999;font-family:Segoe UI,system-ui,sans-serif';
  ov.innerHTML='<div style="width:340px;background:#12121e;border:1px solid #252540;border-radius:16px;padding:28px 24px">'
    +'<div style="font-weight:700;color:#e8e8f8;font-size:15px;margin-bottom:16px">Alterar senha</div>'
    +'<div id="ts-err" style="display:none;background:#ef444418;border:1px solid #ef444440;border-radius:8px;padding:8px 12px;font-size:12px;color:#ef4444;margin-bottom:12px;text-align:center"></div>'
    +'<input id="ts-n1" type="password" placeholder="Nova senha (mín. 6 caracteres)" style="width:100%;background:#18182c;color:#e8e8f8;border:1px solid #252540;border-radius:10px;padding:11px 14px;font-size:13px;margin-bottom:10px;box-sizing:border-box">'
    +'<input id="ts-n2" type="password" placeholder="Confirme a nova senha" style="width:100%;background:#18182c;color:#e8e8f8;border:1px solid #252540;border-radius:10px;padding:11px 14px;font-size:13px;margin-bottom:14px;box-sizing:border-box">'
    +'<div style="display:flex;gap:8px">'
    +'<button id="ts-cancel" style="flex:1;padding:11px;border-radius:10px;border:1px solid #252540;background:none;color:#9090c0;font-size:13px;cursor:pointer">Cancelar</button>'
    +'<button id="ts-ok" style="flex:1;padding:11px;border-radius:10px;border:none;background:linear-gradient(135deg,#60a5fa,#818cf8);color:#fff;font-weight:700;font-size:13px;cursor:pointer">Salvar</button>'
    +'</div></div>';
  document.body.appendChild(ov);
  const err=document.getElementById('ts-err');
  document.getElementById('ts-cancel').onclick=()=>ov.remove();
  document.getElementById('ts-ok').onclick=async()=>{
    const n1=document.getElementById('ts-n1').value, n2=document.getElementById('ts-n2').value;
    if(n1.length<6){err.textContent='A senha precisa ter pelo menos 6 caracteres';err.style.display='block';return;}
    if(n1!==n2){err.textContent='As senhas não conferem';err.style.display='block';return;}
    let sess=null;try{sess=JSON.parse(localStorage.getItem('sb_sess'));}catch(_){}
    if(!sess){err.textContent='Sessão expirada — entre novamente';err.style.display='block';return;}
    const r=await fetch(SUPA_URL+'/auth/v1/user',{method:'PUT',headers:_sbHeaders(sess.t),body:JSON.stringify({password:n1})});
    if(r.ok){ov.remove();alert('Senha alterada com sucesso!');}
    else{const j=await r.json().catch(()=>({}));err.textContent='Erro: '+(j.msg||j.error_description||('HTTP '+r.status));err.style.display='block';}
  };
}

async function _sbBoot(){
  let sess=null; try{sess=JSON.parse(localStorage.getItem('sb_sess'));}catch(_){}
  if(!sess||!sess.t||Date.now()>(sess.exp||0)-60000){
    localStorage.removeItem('sb_sess');
    await _showLogin();
    sess=JSON.parse(localStorage.getItem('sb_sess'));
  }
  const pr=await fetch(SUPA_URL+'/rest/v1/perfis?select=*&login=eq.'+encodeURIComponent(sess.e),{headers:_sbHeaders(sess.t)});
  if(pr.status===401){localStorage.removeItem('sb_sess');await _showLogin('Sess\\u00e3o expirada — entre novamente');return _sbBoot();}
  const perfis=await pr.json();
  if(!perfis.length)throw new Error('Perfil n\\u00e3o encontrado para '+sess.e+'. Contate o administrador.');
  const p=perfis[0];
  _AUTH={login:p.login,role:p.role,nome:p.nome,entidade:p.entidade||''};
  if(p.role==='regional')_URL_REGIONAL=p.entidade||'';
  if(p.role==='super')_URL_SUPER=p.entidade||null;
  if(p.role==='comercial'){_URL_REGIONAL=p.regional_entidade||'';_URL_COMERCIAL=p.entidade||null;}
  const escopo=p.role==='admin'?'admin':(p.role==='super'?p.entidade:p.super_entidade);
  const cr=await fetch(SUPA_URL+'/rest/v1/dashboard_cache?select=payload&escopo=eq.'+encodeURIComponent(escopo),{headers:_sbHeaders(sess.t)});
  if(cr.status===401){localStorage.removeItem('sb_sess');await _showLogin('Sess\\u00e3o expirada — entre novamente');return _sbBoot();}
  const rows=await cr.json();
  if(!rows.length)throw new Error('Dados n\\u00e3o encontrados para o escopo: '+escopo);
  const pl=rows[0].payload;
  DATA=pl.data;DIG_DATA=pl.dig||[];DIG_ESTRATEGICOS=new Set(pl.estrat||[]);DIG_PERIODO=pl.periodo||'';
}
const __BOOT__=_sbBoot().catch(e=>{
  document.body.innerHTML='<div style="padding:48px;font-family:Segoe UI,sans-serif;color:#e8e8f8;background:#0b0b17;min-height:100vh"><h2>N\\u00e3o foi poss\\u00edvel carregar</h2><p style="color:#9090c0">'+e.message+'</p></div>';
  throw e;
});"""


ADMIN_JS = """<script>
// ── Gerenciamento de usuários (admin) — via RPCs seguras no Supabase ──
async function _adminRpc(fn, args){
  const sess=JSON.parse(localStorage.getItem('sb_sess'));
  const r=await fetch(SUPA_URL+'/rest/v1/rpc/'+fn,{method:'POST',headers:_sbHeaders(sess.t),body:JSON.stringify(args||{})});
  if(!r.ok){const j=await r.json().catch(()=>({}));throw new Error(j.message||('HTTP '+r.status));}
  const txt=await r.text();
  return txt?JSON.parse(txt):null;
}

async function initUsuariosTab(){
  const pg=document.getElementById('pg-usuarios');
  if(!pg)return;
  pg.innerHTML='<div class="sec" style="margin-top:0">Gerenciamento de Usuários</div>'
    +'<div id="adm-box" style="color:var(--muted2);font-size:12px;padding:12px 0">Carregando...</div>';
  try{
    const users=await _adminRpc('admin_listar_usuarios');
    const box=document.getElementById('adm-box');
    if(!users||!users.length){box.textContent='Nenhum usuário encontrado.';return;}
    window._admUsers=users;
    let h='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
      +'<span style="font-size:12px;color:var(--muted2)">'+users.length+' usuário(s)</span>'
      +'<button onclick="_admNovo()" style="padding:8px 16px;border-radius:8px;border:none;background:linear-gradient(135deg,#60a5fa,#818cf8);color:#fff;font-weight:700;font-size:12px;cursor:pointer">+ Novo Usuário</button>'
      +'</div>';
    h+='<div class="tbl-wrap"><table><thead><tr><th>Login</th><th>Nome</th><th>Papel</th><th>Entidade</th><th>Status</th><th>Ações</th></tr></thead><tbody>';
    users.forEach(u=>{
      h+='<tr style="'+(u.bloqueado?'opacity:.5':'')+'">'
        +'<td style="font-size:12px">'+u.login+'</td>'
        +'<td style="font-size:12px;color:var(--muted2)">'+(u.nome||'')+'</td>'
        +'<td><span class="bdg '+(u.role==='admin'?'bdg-blue':'bdg-gray')+'">'+u.role+'</span></td>'
        +'<td style="font-size:12px;color:var(--muted2)">'+(u.entidade||'—')+(u.super_entidade?' <span style="color:var(--muted)">('+u.super_entidade+')</span>':'')+'</td>'
        +'<td>'+(u.bloqueado?'<span class="bdg bdg-red">Bloqueado</span>':'<span class="bdg bdg-gray" style="color:var(--green)">Ativo</span>')+'</td>'
        +'<td style="white-space:nowrap">'
        +'<button class="exp-btn" onclick="_admEditar(\\''+u.login+'\\')">✏️ Editar</button> '
        +'<button class="exp-btn" onclick="_admSenha(\\''+u.login+'\\')">🔑 Nova senha</button> '
        +'<button class="exp-btn" onclick="_admBloq(\\''+u.login+'\\','+(!u.bloqueado)+')">'+(u.bloqueado?'✅ Desbloquear':'⛔ Bloquear')+'</button> '
        +'<button class="exp-btn" style="color:var(--red)" onclick="_admExcluir(\\''+u.login+'\\')">🗑 Excluir</button>'
        +'</td></tr>';
    });
    h+='</tbody></table></div>';
    box.outerHTML=h;
  }catch(e){
    document.getElementById('adm-box').textContent='Erro ao listar: '+e.message;
  }
}

async function _admSenha(login){
  const n=prompt('Nova senha para '+login+' (mínimo 6 caracteres):');
  if(n===null)return;
  if(n.length<6){alert('A senha precisa ter pelo menos 6 caracteres.');return;}
  try{await _adminRpc('admin_reset_senha',{alvo:login,nova:n});alert('Senha de '+login+' alterada!');}
  catch(e){alert('Erro: '+e.message);}
}
async function _admBloq(login,b){
  if(!confirm((b?'Bloquear acesso de ':'Desbloquear acesso de ')+login+'?'))return;
  try{await _adminRpc('admin_bloquear',{alvo:login,bloquear:b});initUsuariosTab();}
  catch(e){alert('Erro: '+e.message);}
}
async function _admExcluir(login){
  if(!confirm('EXCLUIR '+login+'? O acesso será removido imediatamente.'))return;
  try{await _adminRpc('admin_excluir',{alvo:login});initUsuariosTab();}
  catch(e){alert('Erro: '+e.message);}
}

function _admNovo(){
  const sups=(DATA.supers||[]).map(s=>s.nome);
  const iCss='width:100%;background:#18182c;color:#e8e8f8;border:1px solid #252540;border-radius:10px;padding:10px 12px;font-size:13px;margin-bottom:12px;box-sizing:border-box';
  const lCss='font-size:10px;color:#6868a0;font-weight:700;text-transform:uppercase;letter-spacing:.6px;display:block;margin-bottom:4px';
  let ov=document.createElement('div');
  ov.style.cssText='position:fixed;inset:0;background:rgba(5,5,15,.75);display:flex;align-items:center;justify-content:center;z-index:9999;font-family:Segoe UI,system-ui,sans-serif;overflow:auto';
  ov.innerHTML='<div style="width:400px;background:#12121e;border:1px solid #252540;border-radius:16px;padding:26px 24px;max-height:90vh;overflow:auto">'
    +'<div style="font-weight:700;color:#e8e8f8;font-size:15px;margin-bottom:14px">Novo Usuário</div>'
    +'<div id="nv-err" style="display:none;background:#ef444418;border:1px solid #ef444440;border-radius:8px;padding:8px 12px;font-size:12px;color:#ef4444;margin-bottom:12px;text-align:center"></div>'
    +'<label style="'+lCss+'">E-mail (login)</label><input id="nv-email" type="email" placeholder="nome.sobrenome@novapromotora.com" style="'+iCss+'">'
    +'<label style="'+lCss+'">Senha inicial</label><input id="nv-senha" type="text" placeholder="mínimo 6 caracteres" style="'+iCss+'">'
    +'<label style="'+lCss+'">Nome (exibição)</label><input id="nv-nome" style="'+iCss+'">'
    +'<label style="'+lCss+'">Papel</label><select id="nv-role" style="'+iCss+'"><option value="super">Superintendente</option><option value="regional">Regional</option><option value="comercial">Comercial</option><option value="admin">Admin</option></select>'
    +'<div id="nv-sup-w"><label style="'+lCss+'">Superintendente</label><select id="nv-sup" style="'+iCss+'"></select></div>'
    +'<div id="nv-reg-w" style="display:none"><label style="'+lCss+'">Regional</label><select id="nv-reg" style="'+iCss+'"></select></div>'
    +'<div id="nv-com-w" style="display:none"><label style="'+lCss+'">Comercial</label><select id="nv-com" style="'+iCss+'"></select></div>'
    +'<div style="display:flex;gap:8px;margin-top:4px">'
    +'<button id="nv-cancel" style="flex:1;padding:11px;border-radius:10px;border:1px solid #252540;background:none;color:#9090c0;font-size:13px;cursor:pointer">Cancelar</button>'
    +'<button id="nv-ok" style="flex:1;padding:11px;border-radius:10px;border:none;background:linear-gradient(135deg,#60a5fa,#818cf8);color:#fff;font-weight:700;font-size:13px;cursor:pointer">Criar</button>'
    +'</div></div>';
  document.body.appendChild(ov);
  const $=id=>document.getElementById(id);
  const selSup=$('nv-sup');
  sups.forEach(s=>selSup.add(new Option(s,s)));
  function fillRegs(){
    const sup=(DATA.supers||[]).find(s=>s.nome===selSup.value);
    const selReg=$('nv-reg');selReg.innerHTML='';
    if(sup)(sup.regionais||[]).forEach(r=>selReg.add(new Option(r.nome,r.nome)));
    fillComs();
  }
  function fillComs(){
    const sup=(DATA.supers||[]).find(s=>s.nome===selSup.value);
    const reg=sup?(sup.regionais||[]).find(r=>r.nome===$('nv-reg').value):null;
    const selCom=$('nv-com');selCom.innerHTML='';
    if(reg)(reg.comerciais||[]).forEach(c=>selCom.add(new Option(c.nome,c.nome)));
  }
  function toggle(){
    const r=$('nv-role').value;
    $('nv-sup-w').style.display=(r==='super'||r==='regional'||r==='comercial')?'':'none';
    $('nv-reg-w').style.display=(r==='regional'||r==='comercial')?'':'none';
    $('nv-com-w').style.display=r==='comercial'?'':'none';
    if(r==='regional'||r==='comercial')fillRegs();
  }
  $('nv-role').onchange=toggle;
  selSup.onchange=fillRegs;
  $('nv-reg').onchange=fillComs;
  toggle();
  $('nv-cancel').onclick=()=>ov.remove();
  $('nv-ok').onclick=async()=>{
    const role=$('nv-role').value;
    const ent=role==='super'?selSup.value:(role==='regional'?$('nv-reg').value:(role==='comercial'?$('nv-com').value:''));
    const supE=(role==='regional'||role==='comercial')?selSup.value:'';
    const regE=role==='comercial'?$('nv-reg').value:'';
    try{
      await _adminRpc('admin_criar_usuario',{
        p_email:$('nv-email').value.trim().toLowerCase(),
        p_senha:$('nv-senha').value,
        p_nome:$('nv-nome').value.trim(),
        p_role:role,p_entidade:ent,p_super:supE,p_regional:regE});
      ov.remove();initUsuariosTab();
      alert('Usuário criado! Informe o login e a senha inicial para a pessoa.');
    }catch(e){
      const err=$('nv-err');err.textContent='Erro: '+e.message;err.style.display='block';
    }
  };
}

function _admEditar(login){
  const u=(window._admUsers||[]).find(x=>x.login===login);
  if(!u)return;
  const sups=(DATA.supers||[]).filter(s=>!s.eh_dinho||true).map(s=>s.nome);
  const iCss='width:100%;background:#18182c;color:#e8e8f8;border:1px solid #252540;border-radius:10px;padding:10px 12px;font-size:13px;margin-bottom:12px;box-sizing:border-box';
  const lCss='font-size:10px;color:#6868a0;font-weight:700;text-transform:uppercase;letter-spacing:.6px;display:block;margin-bottom:4px';
  let ov=document.createElement('div');
  ov.style.cssText='position:fixed;inset:0;background:rgba(5,5,15,.75);display:flex;align-items:center;justify-content:center;z-index:9999;font-family:Segoe UI,system-ui,sans-serif';
  ov.innerHTML='<div style="width:400px;background:#12121e;border:1px solid #252540;border-radius:16px;padding:26px 24px">'
    +'<div style="font-weight:700;color:#e8e8f8;font-size:15px;margin-bottom:14px">Editar — '+login+'</div>'
    +'<div id="ed-err" style="display:none;background:#ef444418;border:1px solid #ef444440;border-radius:8px;padding:8px 12px;font-size:12px;color:#ef4444;margin-bottom:12px;text-align:center"></div>'
    +'<label style="'+lCss+'">Nome (exibição)</label><input id="ed-nome" style="'+iCss+'">'
    +'<label style="'+lCss+'">Papel</label><select id="ed-role" style="'+iCss+'"><option value="admin">Admin</option><option value="super">Superintendente</option><option value="regional">Regional</option><option value="comercial">Comercial</option></select>'
    +'<div id="ed-sup-w" style="display:none"><label style="'+lCss+'">Superintendente</label><select id="ed-sup" style="'+iCss+'"></select></div>'
    +'<div id="ed-reg-w" style="display:none"><label style="'+lCss+'">Regional</label><select id="ed-reg" style="'+iCss+'"></select></div>'
    +'<div id="ed-com-w" style="display:none"><label style="'+lCss+'">Comercial</label><select id="ed-com" style="'+iCss+'"></select></div>'
    +'<div style="display:flex;gap:8px;margin-top:4px">'
    +'<button id="ed-cancel" style="flex:1;padding:11px;border-radius:10px;border:1px solid #252540;background:none;color:#9090c0;font-size:13px;cursor:pointer">Cancelar</button>'
    +'<button id="ed-ok" style="flex:1;padding:11px;border-radius:10px;border:none;background:linear-gradient(135deg,#60a5fa,#818cf8);color:#fff;font-weight:700;font-size:13px;cursor:pointer">Salvar</button>'
    +'</div></div>';
  document.body.appendChild(ov);
  const $=id=>document.getElementById(id);
  $('ed-nome').value=u.nome||'';
  $('ed-role').value=u.role;
  const selSup=$('ed-sup');
  sups.forEach(s=>selSup.add(new Option(s,s)));
  function fillRegs(){
    const sup=(DATA.supers||[]).find(s=>s.nome===selSup.value);
    const selReg=$('ed-reg');selReg.innerHTML='';
    if(sup)(sup.regionais||[]).forEach(r=>selReg.add(new Option(r.nome,r.nome)));
    fillComs();
  }
  function fillComs(){
    const sup=(DATA.supers||[]).find(s=>s.nome===selSup.value);
    const reg=sup?(sup.regionais||[]).find(r=>r.nome===$('ed-reg').value):null;
    const selCom=$('ed-com');selCom.innerHTML='';
    if(reg)(reg.comerciais||[]).forEach(c=>selCom.add(new Option(c.nome,c.nome)));
  }
  function toggle(){
    const r=$('ed-role').value;
    $('ed-sup-w').style.display=(r==='super'||r==='regional'||r==='comercial')?'':'none';
    $('ed-reg-w').style.display=(r==='regional'||r==='comercial')?'':'none';
    $('ed-com-w').style.display=r==='comercial'?'':'none';
    if(r==='regional'||r==='comercial')fillRegs();
  }
  $('ed-role').onchange=toggle;
  selSup.onchange=fillRegs;
  $('ed-reg').onchange=fillComs;
  // pré-preenche hierarquia atual
  if(u.role==='super'&&u.entidade)selSup.value=u.entidade;
  if(u.role==='regional'){
    if(u.super_entidade)selSup.value=u.super_entidade;
    fillRegs();
    if(u.entidade){
      Array.from($('ed-reg').options).forEach(o=>{if(o.value.toUpperCase()===u.entidade.toUpperCase())$('ed-reg').value=o.value;});
    }
  }
  if(u.role==='comercial'){
    if(u.super_entidade)selSup.value=u.super_entidade;
    fillRegs();
    if(u.regional_entidade){
      Array.from($('ed-reg').options).forEach(o=>{if(o.value.toUpperCase()===u.regional_entidade.toUpperCase())$('ed-reg').value=o.value;});
      fillComs();
    }
    if(u.entidade){
      Array.from($('ed-com').options).forEach(o=>{if(o.value.toUpperCase()===u.entidade.toUpperCase())$('ed-com').value=o.value;});
    }
  }
  toggle();
  $('ed-cancel').onclick=()=>ov.remove();
  $('ed-ok').onclick=async()=>{
    const role=$('ed-role').value;
    const ent=role==='super'?selSup.value:(role==='regional'?$('ed-reg').value:(role==='comercial'?$('ed-com').value:''));
    const supE=(role==='regional'||role==='comercial')?selSup.value:'';
    const regE=role==='comercial'?$('ed-reg').value:'';
    try{
      await _adminRpc('admin_editar_usuario',{alvo:login,p_nome:$('ed-nome').value.trim(),p_role:role,p_entidade:ent,p_super:supE,p_regional:regE});
      ov.remove();initUsuariosTab();
    }catch(e){
      const err=$('ed-err');err.textContent='Erro: '+e.message;err.style.display='block';
    }
  };
}
</script>
</body>"""


def main():
    tpl = TEMPLATE.read_text(encoding='utf-8')

    # 1. Substitui constantes embutidas + bloco de autenticação local pelo loader
    m = re.search(
        r"const DATA=__DADOS_JSON__;.*?"
        r"const _URL_COMERCIAL = \(_AUTH\?\.role === 'comercial' && _AUTH\.entidade\) \? _AUTH\.entidade : null;",
        tpl, re.S)
    if not m:
        print("[ERRO] Bloco de dados/auth não encontrado no template.")
        sys.exit(1)
    loader = (LOADER.replace('__SUPA_URL__', SUPA_URL)
              .replace('__SUPA_KEY__', SUPA_KEY)
              .replace('__LOGO_B64__', LOGO_B64))
    html = tpl[:m.start()] + loader + tpl[m.end():]

    # 2. init() espera o login + carregamento
    init_antigo = "document.addEventListener('DOMContentLoaded', init);"
    if init_antigo not in html:
        print("[ERRO] Hook de init não encontrado.")
        sys.exit(1)
    html = html.replace(init_antigo,
        "document.addEventListener('DOMContentLoaded', ()=>{__BOOT__.then(init);});")

    # 3a. Botão "Alterar senha" ao lado do "Sair"
    html = html.replace(
        '<span id="hp-user-nome"></span>',
        '<span id="hp-user-nome"></span>\n      <button onclick="_sbTrocarSenha()" style="background:none;border:none;color:var(--muted2);cursor:pointer;font-size:11px;padding:2px 6px;border-radius:4px;border:1px solid var(--bdr)" title="Alterar senha">Senha</button>', 1)

    # 3. Logout limpa a sessão Supabase e recarrega (boot mostra o login)
    html = html.replace("function logout(){",
        "function logout(){ localStorage.removeItem('sb_sess');", 1)
    html = html.replace("location.replace('__LOGIN_URL__')", "location.reload()")
    html = html.replace('__LOGIN_URL__', 'index.html')

    # 5. Painel de usuários do admin (sobrescreve initUsuariosTab do template)
    html = html.replace('</body>', ADMIN_JS, 1)

    SAIDA.write_text(html, encoding='utf-8')
    (BASE_DIR / "index.html").write_text(html, encoding='utf-8')
    print(f"[OK] app.html + index.html gerados ({len(html)//1024} KB) — login Supabase Auth + RLS")


if __name__ == '__main__':
    main()
