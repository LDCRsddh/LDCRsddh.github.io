# 星光背景实现笔记

记录 `#field` 这块 canvas 的核心思路。代码都在 `index.html` 里，这里只讲原理。

## 一、基础结构

每颗星是一个普通对象：

```js
{
  x, y,           // 位置
  vx, vy,         // 速度
  r,              // 半径
  mass,           // 质量
  orbitR,         // 专属环绕半径
  a, ph, sp,      // 透明度、相位、闪烁频率
  drift,          // 随机漂移方向
  dir             // 环绕方向：1 或 -1
}
```

初始化时按屏幕面积决定数量：

```js
var count = Math.round(Math.min(260, Math.max(80, (W * H) / 9000)));
```

## 二、质量模型

半径 `r` 在 `0.45 ~ 1.95` 之间随机取值。质量定义为半径的平方：

```js
var mass = r * r;
```

这样大的星星在视觉重量上会被进一步放大，符合直觉。

然后把质量归一化到 `0~1`，映射到环绕半径区间：

```js
var t = clamp((mass - MASS_MIN) / (MASS_MAX - MASS_MIN), 0, 1);
var orbitR = ORBIT_MIN + t * (ORBIT_MAX - ORBIT_MIN);
```

其中：

- `ORBIT_MIN = 54`（最轻的星星）
- `ORBIT_MAX = 148`（最重的星星）

**结果**：鼠标附近会自然形成多层光环，小的在内，大的在外，不会挤在同一个半径上。

## 三、鼠标吸引

鼠标影响半径需要覆盖最外层轨道，所以取：

```js
var ATTRACT_R = ORBIT_MAX + 110;   // 258
```

在影响范围内，把速度分解成径向和切向两部分：

```js
var nx = dx / d,  ny = dy / d;       // 径向单位向量
var tx = -ny * s.dir, ty = nx * s.dir; // 切向单位向量
```

- **切向目标速度** 决定公转快慢：`targetVt = clamp(d * 0.017, 0, 2.2) * s.dir`
- **径向目标速度** 把星星推到它自己的轨道上：`targetVr = clamp((s.orbitR - d) * 0.05, -2.4, 2.4)`

两者合成期望速度：

```js
var desiredVx = tx * targetVt + nx * targetVr;
var desiredVy = ty * targetVt + ny * targetVr;
```

## 四、关键：用速度插值代替施加力

早期版本直接把力加在速度上，导致星星冲到鼠标附近后反复抽搐。  
现在的做法是让当前速度**平滑趋近**期望速度：

```js
var k = 0.075 * ease;
s.vx += (desiredVx - s.vx) * k;
s.vy += (desiredVy - s.vy) * k;
```

其中 `ease` 是平滑权重，边缘为 0，中心附近为 1：

```js
var t = 1 - d / ATTRACT_R;
var ease = t * t * (3 - 2 * t);
```

这一步是整个效果稳定的核心。

## 五、随机漂移

没有鼠标时，星星不能死板地直线移动。给每颗星一个缓慢游走的漂移方向：

```js
s.drift += (Math.random() - 0.5) * 0.03;
s.vx += Math.cos(s.drift) * 0.0042;
s.vy += Math.sin(s.drift) * 0.0042;
```

每帧的增量很小，累积起来就是自然的、无规则的缓慢流动。

## 六、阻尼与限速

```js
s.vx *= 0.982;
s.vy *= 0.982;

var sp2 = s.vx * s.vx + s.vy * s.vy;
if (sp2 > MAX_SPEED * MAX_SPEED) {
  var sp = Math.sqrt(sp2);
  s.vx = s.vx / sp * MAX_SPEED;
  s.vy = s.vy / sp * MAX_SPEED;
}
```

阻尼防止速度无限累积，限速防止极端情况下飞出边界。

## 七、边界环绕

不销毁星星，出了边界就从对面回来：

```js
if (s.x < -30) s.x = W + 30;
if (s.x > W + 30) s.x = -30;
if (s.y < -30) s.y = H + 30;
if (s.y > H + 30) s.y = -30;
```

这样星星数量恒定，不会因为长时间运行而变少。

## 八、绘制

闪烁用正弦波，每颗星的频率与相位独立：

```js
var tw = 0.62 + 0.38 * Math.sin(now * s.sp + s.ph);
var alpha = s.a * tw;
```

半径大于 `1.25` 的星星额外画一层光晕：

```js
if (s.r > 1.25) {
  ctx.beginPath();
  ctx.arc(s.x, s.y, s.r * 3.4, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(' + starColor + ',' + (alpha * 0.055) + ')';
  ctx.fill();
}
```

光晕透明度很低，目的是让亮星有一点呼吸感，而不是发光体。

## 九、性能

- 使用 `devicePixelRatio` 适配高分屏，但上限取 `2`，避免 4K 屏上像素翻倍拖慢渲染
- 位置计算与绘制在同一个循环里，不做多余的对象分配
- 数量上限 260，在普通笔记本上稳定 60fps

## 十、可调参数速查

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| `ORBIT_MIN` | 54 | 最轻星星的环绕半径 |
| `ORBIT_MAX` | 148 | 最重星星的环绕半径 |
| `R_MIN` | 0.45 | 星星最小半径 |
| `R_MAX` | 1.95 | 星星最大半径 |
| `ATTRACT_R` | `ORBIT_MAX + 110` | 鼠标影响半径 |
| `MAX_SPEED` | 4 | 速度上限 |

---
