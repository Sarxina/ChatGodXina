--[[ This script provides an a painless way of triggering "talking" movement on a source.
Rather than manually controlling movement with websockets, you can just enable and disbale the
movement as needed

I made this because audio triggered movement (like DougDoug uses) requires a dedicated virtual audio cable
for the pygame, and this is less janky imo than chaining to Move Transform filters together for every source.
Audio triggered is probobly better if you can make it work, but I think this looks pretty good.

To use
1: Put a filter named "Chat God Talk" on any source you want to be animated this way
it doesn't matter what kind, I just use a blank move
NOTE: Its reccomend you put it on a group, rather than the image itself, for more consistent motion
2: Go to Tools -> Scripts -> + (Add Scripts) and add this
3: The animation will perform when the filter is visble, and cease when it isn't
4: ChatGodXina will look for "CGX Group" where X is the Chat God #, and send a websocket request to enable
the filter when it wnants to play the animation

Feel free to fiddle with the parameters to get an animation to your liking

]]

obs = obslua

local bounce_targets = {}
local bounce_timer_ms = 40

local bounce_phase = {}
local bounce_speed = 2 * math.pi / 250  -- full cycle every 250ms

local function bounce_tick()
    local now = obs.os_gettime_ns() / 1e6  -- time in ms

    for source_name, sceneitem in pairs(bounce_targets) do
      local t0 = bounce_phase[source_name] or now
      local phase = (now - t0) * bounce_speed

      local scale = 1 + 0.06 * math.sin(phase) ^ 3
      local vec = obs.vec2()
      vec.x = scale
      vec.y = 2 - scale  -- keep inverse bounce effect

      obs.obs_sceneitem_set_scale(sceneitem, vec)
      bounce_phase[source_name] = t0
    end
  end

local function is_filter_enabled(source, filter_name)
  local filter = obs.obs_source_get_filter_by_name(source, filter_name)
  if not filter then return false end
  local enabled = obs.obs_source_enabled(filter)
  obs.obs_source_release(filter)
  return enabled
end

local function update_bounce_targets()
  --- Recursively looks at scene sources --
  local function scan_scene(scene_source, active_targets)
    local scene = obs.obs_scene_from_source(scene_source)
    if not scene then return end

    local items = obs.obs_scene_enum_items(scene)
    for _, item in ipairs(items) do
      local source = obs.obs_sceneitem_get_source(item)
      local source_name = obs.obs_source_get_name(source)
      local source_id = obs.obs_source_get_id(source)

      if is_filter_enabled(source, 'Chat God Talk') then
        active_targets[source_name] = item
      elseif source_id == 'scene' then
        scan_scene(source, active_targets)
      end
    end
    obs.sceneitem_list_release(items)
  end

  local current_scene_source = obs.obs_frontend_get_current_scene()
  local active_targets = {}
  scan_scene(current_scene_source, active_targets)
  bounce_targets = active_targets
end

function script_load(settings)
  obs.timer_add(update_bounce_targets, 25)
  obs.timer_add(bounce_tick, bounce_timer_ms)
end
