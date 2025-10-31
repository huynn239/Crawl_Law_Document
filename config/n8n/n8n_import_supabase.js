// N8N Code Node - Import to Supabase
// Input: result_supabase.json content

const documents = $input.all();

for (const doc of documents) {
  const data = doc.json;
  
  // 1. Insert/Update doc_urls
  const urlResult = await $('Supabase').insert({
    table: 'doc_urls',
    data: {
      url: data.url,
      status: 'crawled'
    },
    onConflict: 'url',
    returning: ['id', 'doc_id']
  });
  
  const docUrlId = urlResult[0].id;
  
  // 2. Check latest version
  const latestVersion = await $('Supabase').select({
    table: 'doc_metadata',
    columns: ['version', 'content_hash', 'ngay_cap_nhat'],
    filters: {
      doc_url_id: docUrlId
    },
    orderBy: 'version DESC',
    limit: 1
  });
  
  // 3. Decide: insert new version or skip
  let shouldInsert = false;
  
  if (latestVersion.length === 0) {
    // First time
    shouldInsert = true;
  } else {
    const latest = latestVersion[0];
    
    // Check if changed
    if (data.content_hash !== latest.content_hash) {
      shouldInsert = true;
    } else if (data.ngay_cap_nhat && data.ngay_cap_nhat > latest.ngay_cap_nhat) {
      shouldInsert = true;
    }
  }
  
  // 4. Insert if needed
  if (shouldInsert) {
    await $('Supabase').insert({
      table: 'doc_metadata',
      data: {
        doc_url_id: docUrlId,
        so_hieu: data.so_hieu,
        loai_van_ban: data.loai_van_ban,
        linh_vuc: data.linh_vuc,
        noi_ban_hanh: data.noi_ban_hanh,
        nguoi_ky: data.nguoi_ky,
        ngay_ban_hanh: data.ngay_ban_hanh,
        ngay_hieu_luc: data.ngay_hieu_luc,
        tinh_trang: data.tinh_trang,
        raw_data: data.raw_data,
        content_hash: data.content_hash
      }
    });
    
    console.log(`✅ Inserted new version for ${data.url}`);
  } else {
    console.log(`⏭️ Skipped (no changes) ${data.url}`);
  }
}

return documents;
