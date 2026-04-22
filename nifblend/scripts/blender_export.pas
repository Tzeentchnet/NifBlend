{
  NifBlend xEdit companion script.

  Walks every worldspace placement record (REFR/ACHR/PGRE/PMIS/PHZD/
  PARW/PBAR/PBEA/PCON/PFLA) in the active selection and emits one CSV
  row per record:

    model_path,X,Y,Z,rotX,rotY,rotZ,scale

  ARMO references resolve to "Male world model\MOD2"; everything else
  resolves to "Model\MODL". The output is sorted-and-deduped via
  TStringList(dupIgnore) so a cell with 50 references to the same model
  produces 50 rows -- the duplicate rows ARE preserved (different
  positions / rotations / scales). The first line is a comment header
  recognised by nifblend.bridge.cell_csv.parse_cell_csv.

  Adapted from the NifCity Batch nif Importer (CC0).
}
unit UserScript;

const
  sRefSignatures = 'REFR,ACHR,PGRE,PMIS,PHZD,PARW,PBAR,PBEA,PCON,PFLA';
var
  slModels: TStringList;

function Initialize: integer;
begin
  slModels := TStringList.Create;
  slModels.Add('# model,x,y,z,rx,ry,rz,scale');
end;

function Process(e: IInterface): integer;
var
  s: string;
  r: IInterface;
begin
  if Pos(Signature(e), sRefSignatures) = 0 then
    Exit;

  r := BaseRecord(e);

  if not Assigned(r) then
    Exit;

  r := WinningOverride(r);

  if Signature(r) = 'ARMO' then
    s := GetElementEditValues(r, 'Male world model\MOD2')
  else
    s := GetElementEditValues(r, 'Model\MODL');

  if s <> '' then begin
    s := s + ',' +
      GetElementEditValues(e, 'DATA\Position\X') + ',' +
      GetElementEditValues(e, 'DATA\Position\Y') + ',' +
      GetElementEditValues(e, 'DATA\Position\Z') + ',' +
      GetElementEditValues(e, 'DATA\Rotation\X') + ',' +
      GetElementEditValues(e, 'DATA\Rotation\Y') + ',' +
      GetElementEditValues(e, 'DATA\Rotation\Z') + ',' +
      GetElementEditValues(e, 'XSCL');
    slModels.Add(LowerCase(s));
  end;
end;

function Finalize: integer;
begin
  AddMessage('NifBlend cell export: ' + IntToStr(slModels.Count - 1) + ' references');
  slModels.SaveToFile('nifblend_cell.csv');
  slModels.Free;
end;

end.
