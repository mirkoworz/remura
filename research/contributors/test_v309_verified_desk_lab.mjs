import test from 'node:test';
import assert from 'node:assert/strict';
import {renderVerifiedDeskV308,PILOT_RELEASE} from './v308_verified_desk_lab.mjs';
const owner={verified:true,role:'OWNER',slot:'owner',can_read:true,can_write:false};
const member={verified:true,role:'CONTRIBUTOR',slot:'friend-a',can_read:true,can_write:false};
const invited={verified:true,role:'INVITED',slot:'friend-b',can_read:true,can_write:true};
test('new release banner appears once on every allowed document',()=>{
 for(const [path,profile] of [['/owner/',owner],['/owner/levels/',owner],['/contributors/',member],['/contributors/levels/',member],['/join/',invited]]){
  const html=renderVerifiedDeskV308(path,profile);
  assert.equal(typeof html,'string');
  assert.equal((html.match(/<div class="version">/g)||[]).length,1);
  assert.ok(html.includes(PILOT_RELEASE.updatedAt));
  assert.ok(html.includes('REMURA V30.9 LAB'));
  assert.ok(!html.includes('REMURA Contributors v1.10 LAB'));
 }
});
test('new adapter rejects invalid or cross-role navigation',()=>{
 for(const [path,profile] of [['/owner/',member],['/contributors/',owner],['/join/',member],['/owner/',invited],['/join/',{...invited,slot:'friend-a'}],['/owner/',{...owner,verified:false}],['/owner/',{...owner,can_read:false}],['/owner/intelligence/',owner]]){
  assert.equal(renderVerifiedDeskV308(path,profile),null);
 }
});
test('new banner does not open write gates or reveal OWNER forms',()=>{
 const html=renderVerifiedDeskV308('/contributors/levels/',member);
 assert.ok(html.includes('data-write="false"'));
 assert.ok(!html.includes('id="invite"'));
 assert.ok(!html.includes('id="review"'));
 const o=renderVerifiedDeskV308('/owner/levels/',owner);
 assert.ok(!o.includes('id="invite"'));
});
