/**
 * 生产环境：在微信公众平台配置「request 合法域名」后，须与这里一致（HTTPS）。
 * 开发调试：真机与体验版仍须使用已备案 HTTPS 域名（不可使用 localhost）。
 * 若需临时指向测试网关，改为 `https://你的测试域` 并在公众平台添加该域名。
 *
 * publicBrowseMode：小程序正式上架/资质完备前，为 true 时全员可浏览首页与公开行情；
 * 后续改为 false 并在各页恢复「需登录」能力（与 Gateway JWT 策略一致）。
 */
module.exports = {
  apiBase: 'https://htma.newhigh.com.cn',
  publicBrowseMode: true,
};
