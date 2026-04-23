import 'package:flutter/foundation.dart';

/// Represents a single uploaded resource (file)
class ResourceItem {
  final String fileName;
  final String filePath;
  final int? fileSize;
  final String resourceType;
  String query;

  ResourceItem({
    required this.fileName,
    required this.filePath,
    this.fileSize,
    required this.resourceType,
    this.query = '',
  });

  static String typeFromExtension(String fileName) {
    final ext = fileName.split('.').last.toLowerCase();
    if (ext == 'pdf') return 'pdf';
    if (ext == 'pptx' || ext == 'ppt') return 'pptx';
    if (ext == 'mp4' || ext == 'avi' || ext == 'mkv') return 'video';
    if (ext == 'jpg' || ext == 'png' || ext == 'gif'||ext=='jpeg') return 'image';
    return 'website';
  }

  /// Safely parse size_bytes whether it's an int, a Map, or null
  static int? _parseSize(dynamic raw) {
    if (raw == null) return null;
    if (raw is int) return raw;
    if (raw is Map) return raw.values.first as int?;
    return null;
  }

  factory ResourceItem.fromUploadResponse(Map<String, dynamic> json) {
    return ResourceItem(
      fileName: json['filename'] as String? ?? '',
      filePath: json['file_path'] as String? ?? '',
      fileSize: _parseSize(json['size_bytes']),
      resourceType: json['resource_type'] as String? ?? '',
      query: json['query'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'resource_type': resourceType,
        'file_path': filePath,
        'query': query,
      };
}

/// Holds the list of resources selected on the upload screen
/// and the lecture metadata needed for the generate API call
class ResourceStateProvider extends ChangeNotifier {
  List<ResourceItem> _resources = [];
  String _lectureTitle = '';
  String _courseCode = '';

  // Limits
  static const int maxPdfs = 2;
  static const int maxPptx = 2;
  static const int maxVideos = 2;
  static const int maxUrls = 2;
  static const int maxImages = 5;

  // Getters

  List<ResourceItem> get allResources => List.unmodifiable(_resources);
  String get lectureTitle => _lectureTitle;
  String get courseCode => _courseCode;

  bool _canAdd(String type) {
    final count = _resources.where((e) => e.resourceType == type).length;

    switch (type) {
      case 'pdf':
        return count < maxPdfs;
      case 'pptx':
        return count < maxPptx;
      case 'video':
        return count < maxVideos;
      case 'url':
        return count < maxUrls;
      case 'image':
        return count < maxImages;
      default:
        return true;
    }
  }

  bool addResource(ResourceItem resource) {
    final type = resource.resourceType;

    if (!_canAdd(type)) return false;

    _resources.add(resource);
    notifyListeners();
    return true;
  }

  /// Set everything at once when navigating from the upload screen
  void setResources({
    required List<ResourceItem> resources,
    required String lectureTitle,
    required String courseCode,
  }) {
    _resources = [];

    _lectureTitle = lectureTitle;
    _courseCode = courseCode;

    for (var resource in resources) {
      if (_canAdd(resource.resourceType)) {
        _resources.add(resource);
      } else {
        throw Exception(
          'limit reached for ${resource.resourceType} Maximum: ${(resource.resourceType == "image") ? 5 : 2} items',
        );
      }
    }
  }

  /// Update the query for a specific resource by index
  void updateQuery(int index, String query) {
    if (index < 0 || index >= _resources.length) return;
    _resources[index].query = query;
    notifyListeners();
  }

  void removeAt(int index) {
    if (index < 0 || index >= _resources.length) return;
    _resources.removeAt(index);
    notifyListeners();
  }

  void removeResource(ResourceItem resource) {
    _resources.remove(resource);
    notifyListeners();
  }

  void clear() {
    _resources = [];
    _lectureTitle = '';
    _courseCode = '';
    notifyListeners();
  }
}
