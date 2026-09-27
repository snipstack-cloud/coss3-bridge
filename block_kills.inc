// === BRIDGE KILLS: who died, where, and who did it ===
// Installed into _misc_DoDamage (lib/miscext2.script), right after the death
// gate `if (TObj(pobj2).hp<=0)` has fired OnDeath for the target. This is the
// ONLY place in the engine where victim and killer are both in scope: pobj2 and
// trgHnd are the one who died, pobj and goHnd the one who struck (goHnd may be 0
// for round damage without an owner), weapkind the weapon. OnDeath and
// DeathStage1 fire later, when the attackers have already picked new targets,
// and the victim never stores who hit it - the engine only credits the killer
// (TObj(pobj).kill above).
//
// Written into the named parser br_kills as a ring of 48 events, plain text
// 'seq,gt,vpl,vcls,vx,vy,kpl,kcls,kx,ky,w'. Classes are LETTERS decided here
// with the engine constants, because gc_obj_usage_* live in the engine and
// their numbers are not knowable from python: P peasant, I infantry, S shooter,
// C cavalry, G gun, B building, O other, '-' no killer. Weapon: U bullet,
// A arrow, F fire arrow, M everything else (melee, cannon ball).
// The human state block hands the ring to python once a game second and clears
// it when a new match starts. Deaths that do not pass through damage - hunger,
// disbanding, capture - are NOT here on purpose: the map counter still counts
// them, and the gap between the two is itself a fact worth reading.
// No Cyrillic here: the installer writes latin-1.
var brkw : Integer = GetMapWidth;
var brkh : Integer = GetMapHeight;
var brkhw : Integer = brkw div 2;
var brkhh : Integer = brkh div 2;
var brkp : Integer = ParserSelectByKey('br_kills');
if (brkp = 0) then
brkp := ParserCreate('br_kills');
var brkn : Integer = ParserGetIntValueByKeyByHandle(brkp, 'n') + 1;
ParserSetIntValueByKeyByHandle(brkp, 'n', brkn);
// The victim. Separate ifs, not a case: one-line case branches have brought a
// state down in this language before, and this is the same reader.
var brkvu : Integer = gObjProp[TObj(pobj2).cid][TObj(pobj2).id].usage;
var brkvc : String = 'O';
if (brkvu = gc_obj_usage_peasant) then
brkvc := 'P';
if (brkvu = gc_obj_usage_lightinfantry) or (brkvu = gc_obj_usage_weak) or (brkvu = gc_obj_usage_grenadier) then
brkvc := 'I';
if (brkvu = gc_obj_usage_shooter) or (brkvu = gc_obj_usage_archer) then
brkvc := 'S';
if (brkvu = gc_obj_usage_fasthorse) or (brkvu = gc_obj_usage_hardhorse) or (brkvu = gc_obj_usage_horseshooter) then
brkvc := 'C';
if (brkvu = gc_obj_usage_cannon) or (brkvu = gc_obj_usage_mcannon) or (brkvu = gc_obj_usage_mortar) or (brkvu = gc_obj_usage_supermortar) then
brkvc := 'G';
if (gObjProp[TObj(pobj2).cid][TObj(pobj2).id].bbuilding) then
brkvc := 'B';
var brkvx : Integer = floor((GetGameObjectPositionXByHandle(trgHnd) + brkhw) * 16 / brkw);
var brkvz : Integer = floor((GetGameObjectPositionZByHandle(trgHnd) + brkhh) * 16 / brkh);
if (brkvx < 0) then
brkvx := 0;
if (brkvx > 15) then
brkvx := 15;
if (brkvz < 0) then
brkvz := 0;
if (brkvz > 15) then
brkvz := 15;
// The killer, when there is one.
var brkkpl : Integer = -1;
var brkkc : String = '-';
var brkkx : Integer = -1;
var brkkz : Integer = -1;
if (pobj <> nil) then
begin
   brkkpl := TObj(pobj).pl;
   var brkku : Integer = gObjProp[TObj(pobj).cid][TObj(pobj).id].usage;
   brkkc := 'O';
   if (brkku = gc_obj_usage_peasant) then
   brkkc := 'P';
   if (brkku = gc_obj_usage_lightinfantry) or (brkku = gc_obj_usage_weak) or (brkku = gc_obj_usage_grenadier) then
   brkkc := 'I';
   if (brkku = gc_obj_usage_shooter) or (brkku = gc_obj_usage_archer) then
   brkkc := 'S';
   if (brkku = gc_obj_usage_fasthorse) or (brkku = gc_obj_usage_hardhorse) or (brkku = gc_obj_usage_horseshooter) then
   brkkc := 'C';
   if (brkku = gc_obj_usage_cannon) or (brkku = gc_obj_usage_mcannon) or (brkku = gc_obj_usage_mortar) or (brkku = gc_obj_usage_supermortar) then
   brkkc := 'G';
   if (gObjProp[TObj(pobj).cid][TObj(pobj).id].bbuilding) then
   brkkc := 'B';
   brkkx := floor((GetGameObjectPositionXByHandle(goHnd) + brkhw) * 16 / brkw);
   brkkz := floor((GetGameObjectPositionZByHandle(goHnd) + brkhh) * 16 / brkh);
   if (brkkx < 0) then
   brkkx := 0;
   if (brkkx > 15) then
   brkkx := 15;
   if (brkkz < 0) then
   brkkz := 0;
   if (brkkz > 15) then
   brkkz := 15;
end;
var brkwc : String = 'M';
if (weapkind = gc_obj_weapon_kind_bullet) then
brkwc := 'U';
if (weapkind = gc_obj_weapon_kind_arrow) then
brkwc := 'A';
if (weapkind = gc_obj_weapon_kind_firearrow) then
brkwc := 'F';
ParserSetValueByKeyByHandle(brkp, 'e' + IntToStr(brkn mod 48),
     IntToStr(brkn) + ',' + IntToStr(Round(GetGameTime)) + ',' +
     IntToStr(TObj(pobj2).pl) + ',' + brkvc + ',' +
     IntToStr(brkvx) + ',' + IntToStr(brkvz) + ',' +
     IntToStr(brkkpl) + ',' + brkkc + ',' +
     IntToStr(brkkx) + ',' + IntToStr(brkkz) + ',' + brkwc);
// === END BRIDGE KILLS ===
