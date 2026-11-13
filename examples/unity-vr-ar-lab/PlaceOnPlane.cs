using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

[RequireComponent(typeof(ARRaycastManager))]
public class PlaceOnPlane : MonoBehaviour
{
    [SerializeField]
    private GameObject _spawnObject;

    private ARRaycastManager _raycastManager;
    private readonly List<ARRaycastHit> _hitResults = new List<ARRaycastHit>();
    private bool _isPlaced;

    private void Awake()
    {
        _raycastManager = GetComponent<ARRaycastManager>();
        if (_spawnObject == null)
        {
            Debug.LogError("请在 PlaceOnPlane 的 Spawn Object 中指定 Base 预制体。", this);
            enabled = false;
        }
    }

    private void Update()
    {
        if (_isPlaced)
            return;

        Vector2 screenPosition;
        if (Input.touchCount > 0)
        {
            Touch touch = Input.GetTouch(0);
            if (touch.phase != TouchPhase.Began)
                return;
            screenPosition = touch.position;
        }
        else
        {
#if UNITY_EDITOR
            // 编辑器允许鼠标点击，避免没有触摸时直接访问 GetTouch(0)。
            if (!Input.GetMouseButtonDown(0))
                return;
            screenPosition = Input.mousePosition;
#else
            return;
#endif
        }

        // 只有点击已识别平面的边界内，才放置一次完整场景。
        if (_raycastManager.Raycast(screenPosition, _hitResults, TrackableType.PlaneWithinPolygon))
        {
            Instantiate(_spawnObject, _hitResults[0].pose.position, Quaternion.identity);
            _isPlaced = true;
        }
    }
}
